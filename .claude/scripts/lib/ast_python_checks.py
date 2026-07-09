#!/usr/bin/env python3
"""AST-based checks for Python source files.

Called from bash check-*.sh scripts. Reads source files, emits JSONL findings
to stdout (one JSON object per line).

Usage:
    python3 ast-python-checks.py <check-name> <file1> [<file2> ...]

Where <check-name> is one of:
    el-01, el-02          exception chaining / swallow
    tel-02, tel-06        telemetry decorators / tests
    pt-01, pt-08, pt-11   patterns
    con-01                repeated string literals
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path


def emit(
    rule: str, severity: str, file: str, line: int, message: str, suggestion: str = ""
) -> None:
    print(
        json.dumps(
            {
                "rule": rule,
                "severity": severity,
                "file": file,
                "line": line,
                "message": message,
                "suggestion": suggestion,
            }
        )
    )


def parse_file(path: str) -> ast.Module | None:
    try:
        source = Path(path).read_text(encoding="utf-8")
        return ast.parse(source, filename=path)
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return None


# ---------- PY-EL-01: raise X from e when raising DIFFERENT exception ----------


def check_el_01(path: str, tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        handler_name = node.name  # the caught exception variable, may be None
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Raise):
                continue
            # bare `raise` — PASS (preserves cause)
            if inner.exc is None:
                continue
            # `raise e` where e is the handler var — PASS (same exception)
            if (
                isinstance(inner.exc, ast.Name)
                and handler_name
                and inner.exc.id == handler_name
            ):
                continue
            # raising a *call* to the same var, e.g. `raise e()` (rare) — PASS
            if (
                isinstance(inner.exc, ast.Call)
                and isinstance(inner.exc.func, ast.Name)
                and handler_name
                and inner.exc.func.id == handler_name
            ):
                continue
            # different exception without `from e` → FLAG
            if inner.cause is None:
                emit(
                    "PY-EL-01",
                    "FLAG",
                    path,
                    inner.lineno,
                    "Raising different exception inside except — use `raise X from e` to preserve cause",
                )


# ---------- PY-EL-02: except body must end with raise or explicit suppression ----------


def check_el_02(path: str, tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not node.body:
            continue
        last = node.body[-1]
        # last statement is Raise → PASS
        if isinstance(last, ast.Raise):
            continue
        # last statement is Return of a variable named e / err / exc → likely intentional propagation → PASS
        if (
            isinstance(last, ast.Return)
            and isinstance(last.value, ast.Name)
            and last.value.id in {"e", "err", "exc"}
        ):
            continue
        # explicit `pass` and only `pass` in body → obvious swallow → FLAG
        emit(
            "PY-EL-02",
            "FLAG",
            path,
            node.lineno,
            "except block does not end with `raise` — swallowing? Add re-raise or comment justifying suppression",
        )


# ---------- PY-TEL-02: public *Client methods have @record_metrics ----------


def check_tel_02(path: str, tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.endswith("Client"):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name.startswith("_"):
                continue
            has_record = any(
                (
                    isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Name)
                    and d.func.id == "record_metrics"
                )
                or (isinstance(d, ast.Name) and d.id == "record_metrics")
                for d in item.decorator_list
            )
            if not has_record:
                emit(
                    "PY-TEL-02",
                    "BLOCK",
                    path,
                    item.lineno,
                    f"Public method `{node.name}.{item.name}` missing @record_metrics decorator",
                )


# ---------- PY-TEL-06: test files that assert record_request_metric calls ----------


def check_tel_06_test_asserts(path: str, tree: ast.Module) -> bool:
    """Returns True if the test file asserts record_request_metric was called."""
    src = ast.dump(tree)
    return "record_request_metric" in src


# ---------- PY-PT-08: public functions/methods have type hints ----------


def check_pt_08(path: str, tree: ast.Module) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # skip private functions
        if node.name.startswith("_") and node.name != "__init__":
            continue
        # skip @classmethod first-arg conventionally named "cls"
        missing: list[str] = []
        # check return annotation
        if node.returns is None and node.name != "__init__":
            missing.append("return type")
        # check arg annotations (excluding self/cls)
        for arg in node.args.args:
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                missing.append(f"param `{arg.arg}`")
        # also check keyword-only, positional-only, and vararg annotations
        for arg in getattr(node.args, "kwonlyargs", []):
            if arg.annotation is None:
                missing.append(f"keyword-only `{arg.arg}`")
        for arg in getattr(node.args, "posonlyargs", []):
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                missing.append(f"positional-only `{arg.arg}`")
        if node.args.vararg and node.args.vararg.annotation is None:
            missing.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg and node.args.kwarg.annotation is None:
            missing.append(f"**{node.args.kwarg.arg}")

        # Emit one finding per function (not per arg) so downstream isn't spammed
        if missing:
            joined = ", ".join(missing)
            emit(
                "PY-PT-08",
                "FLAG",
                path,
                node.lineno,
                f"Public function `{node.name}` missing type annotations: {joined}",
            )


# ---------- PY-CON-01: repeated string literals ----------


def check_con_01(
    path: str, tree: ast.Module, threshold: int = 3, min_len: int = 4
) -> None:
    # FP-D-01: skip generated/model files where schema keys legitimately repeat.
    GENERATED_PATTERNS = ("_models.py", "_generated.py")
    GENERATED_API_SUFFIX = "_api.py"
    fname = Path(path).name
    if fname.endswith(GENERATED_PATTERNS):
        return
    # `_<something>_api.py` (starts with underscore, ends with _api.py) → generated OpenAPI client
    if fname.startswith("_") and fname.endswith(GENERATED_API_SUFFIX):
        return
    # Skip prefixes: URLs, test/example placeholders, SPDX/doc markers.
    # Must be exact URL scheme match — not `httpx` or `http_pool`.
    URL_PREFIXES = ("http://", "https://", "ftp://", "sftp://", "ssh://", "file://")
    SKIP_PREFIXES = ("test-", "SPDX", "@example")
    # FP-D-01: minimum length 4 (was 4; enforce hard floor of 3 per plan)
    effective_min_len = max(min_len, 3)
    # FP-D-01: per-file cap
    MAX_PER_FILE = 3

    # FP-K-01: load the PR's added-lines set (if orchestrate provided it) so
    # we only count string occurrences that the PR actually introduces. Prevents
    # penalizing an unrelated edit for pre-existing repetitions.
    added_lines_for_file: set[int] | None = None
    added_lines_file = os.environ.get("ADDED_LINES_FILE", "")
    if added_lines_file and Path(added_lines_file).is_file():
        added_lines_for_file = set()
        try:
            with open(added_lines_file, encoding="utf-8") as fh:
                for entry in fh:
                    entry = entry.strip()
                    if not entry or ":" not in entry:
                        continue
                    p, _, ln = entry.rpartition(":")
                    if p == path:
                        try:
                            added_lines_for_file.add(int(ln))
                        except ValueError:
                            continue
        except OSError:
            added_lines_for_file = None
    # If the caller didn't provide a diff scope, fall back to legacy behavior
    # (count all occurrences). Bats tests exercise the check without an
    # orchestrate wrapper, so we keep backward-compat.

    counts: dict[str, list[int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            if len(v) < effective_min_len:
                continue
            if v.startswith(URL_PREFIXES):
                continue
            if v.startswith(SKIP_PREFIXES):
                continue
            counts.setdefault(v, []).append(node.lineno)
    emitted = 0
    for literal, lines in counts.items():
        if emitted >= MAX_PER_FILE:
            break
        if len(lines) < threshold:
            continue
        # FP-K-01: require at least one occurrence to live on a PR-added line.
        # Without this, an unrelated edit is credited for the repetition that
        # already existed. If we have no diff scope, allow the legacy path.
        if added_lines_for_file is not None:
            added_occurrences = [ln for ln in lines if ln in added_lines_for_file]
            if not added_occurrences:
                continue
            anchor_line = added_occurrences[0]
        else:
            anchor_line = lines[0]
        emit(
            "PY-CON-01",
            "FLAG",
            path,
            anchor_line,
            f"String literal {literal!r} appears {len(lines)}× — extract module-level constant",
            suggestion=f"e.g., _CONSTANT_NAME = {literal!r}",
        )
        emitted += 1


# ---------- PY-PT-04: module has any Exception subclass (AST-based) ----------


def check_pt_04(module_dir: str) -> bool:
    """FP-C-02: return True if any .py file in the module directory (recursive)
    defines a class subclassing Exception (directly or via a name ending in
    'Error' / 'Exception'). Callers can use this as a soft check before
    emitting PY-PT-04.
    """
    p = Path(module_dir)
    if not p.is_dir():
        return False
    for py in p.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        tree = parse_file(str(py))
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                base_name = None
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if not base_name:
                    continue
                if base_name == "Exception" or base_name == "BaseException":
                    return True
                # accept anything ending in Error/Exception as an exception hierarchy
                if base_name.endswith("Error") or base_name.endswith("Exception"):
                    return True
    return False


# ---------- PY-PT-01: create_client factory exists ----------


def check_pt_01(module_dir: str) -> bool:
    """Check if module has create_client() function (returns True if found)."""
    p = Path(module_dir)
    if not p.is_dir():
        return False
    # scan module-level defs across all .py files
    for py in p.glob("*.py"):
        if py.name.startswith("_") and py.name != "__init__.py":
            continue
        tree = parse_file(str(py))
        if tree is None:
            continue
        for node in tree.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name.startswith("create_")
                and node.name.endswith("client")
            ):
                return True
    return False


# ---------- __all__ extraction (used by breaking-detector.py) ----------


def extract_all(tree: ast.Module) -> list[str]:
    """Extract the __all__ list from a module AST."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    return [
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
    return []


def extract_public_class_methods(
    tree: ast.Module,
) -> dict[str, dict[str, tuple]]:
    """Return {ClassName: {method_name: signature_tuple}}.

    signature_tuple = (
        positional_args,        # names of positional args (self/cls excluded)
        kwonly_args,            # names of keyword-only args
        vararg_kwarg_flags,     # ["*args", "**kwargs"] if present
        return_ann,             # repr of return annotation, or None
        num_pos_defaults,       # count of positional args with a default value
        num_kwonly_required,    # count of keyword-only args WITHOUT a default
    )
    """
    result: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_"):
            continue
        methods: dict = {}
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name.startswith("_") and item.name != "__init__":
                continue
            pos_args = [a.arg for a in item.args.args if a.arg not in {"self", "cls"}]
            kwonly = [a.arg for a in item.args.kwonlyargs]
            varflags: list[str] = []
            if item.args.vararg:
                varflags.append(f"*{item.args.vararg.arg}")
            if item.args.kwarg:
                varflags.append(f"**{item.args.kwarg.arg}")
            ret = ast.unparse(item.returns) if item.returns else None
            # Count of positional args that have a default value. Needed by
            # the breaking-change detector to tell an additive change (new
            # optional trailing arg) from a breaking one (new required arg).
            num_pos_defaults = len(item.args.defaults)
            # kwonly defaults: kw_defaults has None entries for required kwonly
            num_kwonly_required = sum(
                1 for d in item.args.kw_defaults if d is None
            )
            methods[item.name] = (
                pos_args,
                kwonly,
                varflags,
                ret,
                num_pos_defaults,
                num_kwonly_required,
            )
        if methods:
            result[node.name] = methods
    return result


def extract_dataclass_fields(tree: ast.Module) -> dict[str, list[str]]:
    """Return {DataclassName: [field_names]} for classes decorated with @dataclass
    or @dataclasses.dataclass."""
    result: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        is_dc = False
        for d in node.decorator_list:
            # bare @dataclass
            if isinstance(d, ast.Name) and d.id == "dataclass":
                is_dc = True
                break
            # @dataclass(frozen=True) or @dataclass()
            if (
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Name)
                and d.func.id == "dataclass"
            ):
                is_dc = True
                break
            # @dataclasses.dataclass
            if isinstance(d, ast.Attribute) and d.attr == "dataclass":
                is_dc = True
                break
            # @dataclasses.dataclass(...)
            if (
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr == "dataclass"
            ):
                is_dc = True
                break
        if not is_dc:
            continue
        fields: list[str] = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append(item.target.id)
        if fields:
            result[node.name] = fields
    return result


# ---------- dispatcher ----------

CHECKS = {
    "el-01": check_el_01,
    "el-02": check_el_02,
    "tel-02": check_tel_02,
    "pt-08": check_pt_08,
    "con-01": check_con_01,
}


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "Usage: ast-python-checks.py <check-name> <file1> [<file2> ...]",
            file=sys.stderr,
        )
        return 2
    check_name = argv[1]
    files = argv[2:]

    # FP-C-02: pt-04 has a different signature (module dir, not files) and
    # returns a boolean via exit code (0 = has exceptions, 1 = none found).
    if check_name == "pt-04":
        module_dir = files[0]
        return 0 if check_pt_04(module_dir) else 1

    # FP-R-01: docstring-lines prints "1" for every line number that falls
    # inside a module/class/function docstring, so line-based checks (e.g.
    # check-hardcode HC-01) can skip URLs that live in documentation examples.
    if check_name == "docstring-lines":
        for f in files:
            tree = parse_file(f)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(
                    node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    continue
                doc = ast.get_docstring(node, clean=False)
                if not doc:
                    continue
                # The docstring is the first statement's Constant node.
                body = getattr(node, "body", [])
                if not body:
                    continue
                first = body[0]
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    start = first.value.lineno
                    end = getattr(first.value, "end_lineno", start)
                    for ln in range(start, end + 1):
                        print(ln)
        return 0

    # FP-S-01: http-session-lines prints the line number of every
    # requests.Session()/httpx.Client()/AsyncClient() call that is NOT inside
    # __init__ (or a module/class-level assignment). A session created in
    # __init__ is the RECOMMENDED pattern, so HTTP-01 must not fire on it.
    # Only lines printed here are per-invocation sessions worth flagging.
    if check_name == "http-session-lines":
        SESSION_CTORS = {"Session", "Client", "AsyncClient"}
        for f in files:
            tree = parse_file(f)
            if tree is None:
                continue
            # Map every function def to whether it is __init__.
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name == "__init__":
                    continue  # sessions here are the correct pattern
                for sub in ast.walk(node):
                    if (
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr in SESSION_CTORS
                    ):
                        print(sub.lineno)
        return 0

    if check_name not in CHECKS:
        print(f"ERROR: unknown check {check_name}", file=sys.stderr)
        return 2

    fn = CHECKS[check_name]
    for f in files:
        tree = parse_file(f)
        if tree is None:
            continue
        fn(f, tree)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
