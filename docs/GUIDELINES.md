# Python Development Guidelines

## Project Structure
- `src/`: Source code following the src-layout pattern
- `src/sap_cloud_sdk/`: Main package namespace
- `tests/`: Test code mirroring the source structure
- Private implementation modules use underscore prefix (e.g., `_s3.py`, `_models.py`)
- Keep internal packages organized with clear separation of concerns
- Create shared utilities in `core/` for reusable patterns across modules
- Avoid unnecessary nesting - keep structure as flat as possible while maintaining clarity

## Naming Conventions
- Follow PEP 8 naming conventions consistently
- Use descriptive names for variables and functions, avoid single-letter names except for loop counters
- Private methods and attributes use leading underscore (e.g., `_validate_input`)
- Use descriptive file names that reflect functionality (e.g., `_s3.py` for S3 implementation)

## API Design
- Use dataclasses for configuration and data models with proper type annotations
- Separate public API from internal implementation using underscore prefixes
- Keep imports clean - users should import from top-level module packages
- Use dependency injection where appropriate rather than global state
- Separate concerns into dedicated files (models, exceptions, implementations)
- Design for composition over inheritance

## Type Safety
- Use type annotations throughout the codebase (functions, methods, class attributes)
- Leverage `typing` module for complex types (Union, Optional, List, Dict, etc.)
- Use Protocol classes for defining interfaces/contracts
- Enable strict type checking with ty in development
- Use `py.typed` marker files to indicate typed packages
- Use `TypedDict` for structured dictionaries

## Error Handling
- Create domain-specific exception hierarchies inheriting from built-in exceptions
- Use `raise ... from e` for exception chaining to preserve stack traces
- Don't expose internal implementation details in error messages
- Validate inputs early and provide clear validation error messages

## Async/Context Management
- Use context managers (`with` statements) for resource management when applicable
- Consider async variants for I/O-bound operations where it adds value
- Always clean up resources properly (file handles, network connections, etc.)

## Code Quality
- Follow PEP 8 style guidelines
- Prefer composition and dependency injection over global state
- Use descriptive variable names and avoid abbreviations

## Testing
- Use `pytest` as the testing framework
- Organize tests to mirror source code structure
- Use descriptive test names that explain what is being tested, following the `test_<functionality>_<condition>_<expected_result>` pattern

## Documentation
- Use docstrings for all public functions, classes, and modules
- Follow Google or NumPy docstring style consistently
- Include type information in docstrings when not obvious from annotations
- Provide usage examples in docstrings for complex functionality
- Document parameters, return values, and raised exceptions

## Dependencies
- Keep dependencies minimal - avoid heavy frameworks when simple solutions suffice

## Logging
- Use the standard `logging` module
- Create module-level loggers using `logger = logging.getLogger(__name__)`
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Don't log sensitive information (credentials, personal data)
- Use structured logging with consistent formatting
- Log important state changes and error conditions

## Performance Considerations
- Use generators and iterators for memory efficiency with large datasets
- Use appropriate data structures for the use case

## Telemetry
- All SDK modules should include telemetry instrumentation for observability
- Use the centralized `@record_metrics` decorator from `core/telemetry`

### Adding Telemetry to a Module
1. Add module constant to `core/telemetry/module.py`
2. Add operation constants to `core/telemetry/operation.py`
3. Apply decorator to client methods:ß
   ```python
   from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

   @record_metrics(Module.MY_MODULE, Operation.MY_OPERATION)
   def my_operation(self):
       # implementation
   ```

### Source Tracking (Optional)
- For modules called by other SDK modules (e.g., auditlog), add `_telemetry_source` parameter:
  ```python
  def __init__(self, transport, _telemetry_source: Optional[Module] = None):
      self._telemetry_source = _telemetry_source
  ```
- When creating the client from another module, pass the source:
  ```python
  self._audit_client = create_auditlog_client(_telemetry_source=Module.OBJECTSTORE)
  ```
- The decorator automatically reads `_telemetry_source` from `self` to track call origin

## Security
- Never log or expose sensitive information (passwords, tokens, etc.)
- Validate all inputs, especially from external sources
- Follow principle of least privilege in code design

## Credential Binding Rotation

BTP service bindings can rotate at runtime. Long-lived clients holding stale credentials will fail with auth errors once the old secrets expire. Every SDK module that reads credentials from mounts or env vars must support rotation.

### Two resilience layers

**Proactive** — check `ConfigFactory.has_changed()` before every credential use. If the mtime of the secret directory changed, re-read the binding and discard any cached tokens or session objects.

**Reactive** — on a credential-rejection error (e.g. HTTP 401 for OAuth modules, S3 `InvalidAccessKeyId`/`SignatureDoesNotMatch` for object store), refresh credentials and retry the operation once.

### Pattern for OAuth2 modules

Token providers and auth classes must accept either a fixed config object **or** a callable (factory) returning the config:

```python
if callable(config) and not isinstance(config, MyConfig):
    self._config_factory: Callable[[], MyConfig] = config
    self._config = config()
else:
    self._config_factory = lambda: config  # static; no rotation tracking
    self._config = config
```

Before serving a cached token, call `_refresh_if_rotated()`:

```python
def _refresh_if_rotated(self) -> None:
    has_changed = getattr(self._config_factory, "has_changed", None)
    if callable(has_changed) and has_changed():
        self._config = self._config_factory()
        self._cached_token = None          # discard stale token
        # rebuild session/client if needed
```

### Pattern for key-based clients (e.g. object store / MinIO)

Credentials are baked into the client at construction time, so the client itself must be rebuilt on rotation. Wrap every public operation in `_execute_with_retry`:

```python
_CREDENTIAL_ERROR_CODES = frozenset({"InvalidAccessKeyId", "SignatureDoesNotMatch"})

def _execute_with_retry(self, fn):
    self._refresh_if_rotated()
    try:
        return fn()
    except S3Error as e:
        if e.code in _CREDENTIAL_ERROR_CODES:
            with self._lock:
                self._creds = self._config_factory()
                self._client = self._create_client()
            return fn()
        raise
```

Use a `threading.Lock` when rebuilding the client to avoid races under concurrent calls.

### Public API factory functions (`create_client`)

- **Auto-detection path** (no explicit `config=`): pass a `ConfigFactory` instance directly to the token provider / auth class. `ConfigFactory` carries `has_changed()` automatically.
- **Explicit `config=` path**: wrap in a static lambda to preserve the factory interface without rotation tracking.

```python
def create_client(*, instance=None, config=None):
    if config is not None:
        credentials = lambda: config  # static, no rotation
    else:
        credentials = _make_config_factory(instance)
    return MyClient(credentials)
```

### `ConfigFactory` contract

`ConfigFactory[C]` (from `sap_cloud_sdk.core.secret_resolver`) reads bindings on every `__call__()` and tracks secret directory mtime via `has_changed()`. To use it, the binding dataclass must:
- Have all fields defaulting to `""` so `binding_cls()` can be called with no args.
- Implement `validate()` raising on missing required fields.

### Testing rotation

Every module that supports rotation must have tests for:
1. **Proactive**: `has_changed()` returns `True` → token/session/client is rebuilt before the next operation.
2. **Reactive** (key-based clients): credential-rejection error on first call → retried once with fresh credentials.
3. **No rebuild**: `has_changed()` returns `False` → existing session/client reused.
4. **Static config**: plain config object (no `has_changed`) → no error, no rotation check.
