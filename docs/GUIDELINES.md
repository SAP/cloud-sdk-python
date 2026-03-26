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
