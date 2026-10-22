#!/usr/bin/env python3
"""Breaking-change detector.

Compares AST of base commit vs HEAD to find:
    - api_removal_detected           removed from __all__
    - method_deletion_on_public_class
    - dataclass_field_deletion
    - public_method_signature_change
    - enum_value_deletion
    - exception_hierarchy_change

Output: JSON on stdout:
{
  "breaking_detected": true|false,
  "kinds": [...],
  "details": [{"kind": "...", "symbol": "...", "file": "...", "line": N}, ...]
}
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

# Import from same directory
sys.path.insert(0, str(Path(__file__).parent))
from ast_python_checks import (
    extract_all,
    extract_public_class_methods,
    extract_dataclass_fields,
)  # noqa: E402


def git_show(sha: str, path: str) -> str | None:
    """Read file content at a given commit. Returns None if not available."""
    # Try direct git show first
    try:
        out = subprocess.run(
            ["git", "show", f"{sha}:{path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout
    except Exception:
        pass
    # Fallback: try to fetch the object first if it's missing
    try:
        subprocess.run(
            ["git", "fetch", "--quiet", "origin", sha],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        out = subprocess.run(
            ["git", "show", f"{sha}:{path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout
    except Exception:
        pass
    return None


def read_head_file(path: str) -> str | None:
    """Read file content from HEAD (working tree)."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def parse_source(source: str, filename: str = "<string>") -> ast.Module | None:
    try:
        return ast.parse(source, filename=filename)
    except SyntaxError:
        return None


def files_changed(base: str, head: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}", "--", "*.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [f for f in out.stdout.strip().split("\n") if f]


def detect(base: str, head: str) -> dict:
    details: list[dict] = []
    kinds: set[str] = set()

    changed = files_changed(base, head)

    for file in changed:
        base_src = git_show(base, file)
        head_src = git_show(head, file) if head != "HEAD" else read_head_file(file)
        if head_src is None and Path(file).exists():
            head_src = read_head_file(file)
        if head_src is None:
            # file deleted
            if base_src:
                base_tree = parse_source(base_src, file)
                if base_tree:
                    for name in extract_all(base_tree):
                        details.append(
                            {
                                "kind": "api_removal_detected",
                                "symbol": name,
                                "file": file,
                                "line": 0,
                            }
                        )
                        kinds.add("api_removal_detected")
            continue

        base_tree = parse_source(base_src, file) if base_src else None
        head_tree = parse_source(head_src, file)
        if base_tree is None or head_tree is None:
            continue

        # __all__ removals
        base_all = set(extract_all(base_tree))
        head_all = set(extract_all(head_tree))
        removed = base_all - head_all
        for name in removed:
            details.append(
                {
                    "kind": "api_removal_detected",
                    "symbol": name,
                    "file": file,
                    "line": 0,
                }
            )
            kinds.add("api_removal_detected")

        # public class method removals + signature changes
        base_classes = extract_public_class_methods(base_tree)
        head_classes = extract_public_class_methods(head_tree)
        for cls_name, base_methods in base_classes.items():
            head_methods = head_classes.get(cls_name, {})
            for mname, base_sig in base_methods.items():
                if mname not in head_methods:
                    details.append(
                        {
                            "kind": "method_deletion_on_public_class",
                            "symbol": f"{cls_name}.{mname}",
                            "file": file,
                            "line": 0,
                        }
                    )
                    kinds.add("method_deletion_on_public_class")
                else:
                    head_sig = head_methods[mname]
                    # Compare all four elements of the signature tuple:
                    # (pos_args, kwonly_args, vararg_flags, return_annotation)
                    if base_sig != head_sig:
                        details.append(
                            {
                                "kind": "public_method_signature_change",
                                "symbol": f"{cls_name}.{mname}",
                                "file": file,
                                "line": 0,
                                "base_sig": {
                                    "pos_args": base_sig[0],
                                    "kwonly_args": base_sig[1],
                                    "var_flags": base_sig[2],
                                    "return": base_sig[3],
                                },
                                "head_sig": {
                                    "pos_args": head_sig[0],
                                    "kwonly_args": head_sig[1],
                                    "var_flags": head_sig[2],
                                    "return": head_sig[3],
                                },
                            }
                        )
                        kinds.add("public_method_signature_change")

        # dataclass field removals
        base_dcs = extract_dataclass_fields(base_tree)
        head_dcs = extract_dataclass_fields(head_tree)
        for dc_name, base_fields in base_dcs.items():
            head_fields = set(head_dcs.get(dc_name, []))
            for field in base_fields:
                if field not in head_fields:
                    details.append(
                        {
                            "kind": "dataclass_field_deletion_on_public_model",
                            "symbol": f"{dc_name}.{field}",
                            "file": file,
                            "line": 0,
                        }
                    )
                    kinds.add("dataclass_field_deletion_on_public_model")

        # enum value removals (best-effort: str Enum classes)
        base_enums = _extract_enums(base_tree)
        head_enums = _extract_enums(head_tree)
        for enum_name, base_values in base_enums.items():
            head_values = set(head_enums.get(enum_name, []))
            for val in base_values:
                if val not in head_values:
                    details.append(
                        {
                            "kind": "enum_value_deletion_on_public_enum",
                            "symbol": f"{enum_name}.{val}",
                            "file": file,
                            "line": 0,
                        }
                    )
                    kinds.add("enum_value_deletion_on_public_enum")

    return {
        "breaking_detected": bool(kinds),
        "kinds": sorted(kinds),
        "details": details,
    }


def _extract_enums(tree: ast.Module) -> dict[str, list[str]]:
    """Extract enum classes and their values.

    Detects classes whose base is exactly Enum, IntEnum, StrEnum, Flag, IntFlag,
    or the same via attribute access (enum.Enum, etc.). Rejects unrelated names
    that happen to contain "Enum" (e.g. NotAnEnum, MyEnumWrapper).
    """
    ENUM_BASE_NAMES = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}
    result: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith("_"):
            continue
        is_enum = False
        for b in node.bases:
            # bare Name: e.g. class Status(Enum)
            if isinstance(b, ast.Name) and b.id in ENUM_BASE_NAMES:
                is_enum = True
                break
            # Attribute: e.g. class Status(enum.Enum)
            if isinstance(b, ast.Attribute) and b.attr in ENUM_BASE_NAMES:
                is_enum = True
                break
        if not is_enum:
            continue
        values: list[str] = []
        for item in node.body:
            # Simple: RED = 1
            if isinstance(item, ast.Assign):
                for tgt in item.targets:
                    if isinstance(tgt, ast.Name):
                        values.append(tgt.id)
            # Annotated: RED: int = 1
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                values.append(item.target.id)
        result[node.name] = values
    return result


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        # default to comparing merge-base of main..HEAD
        base = (
            subprocess.run(
                ["git", "merge-base", "origin/main", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            or "HEAD~1"
        )
        head = "HEAD"
    else:
        base, head = argv[1], argv[2]

    result = detect(base, head)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
