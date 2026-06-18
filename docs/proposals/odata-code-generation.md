# Proposal: OData Code Generation for SAP Cloud SDK Python

## Overview

Add a code generation capability to the SAP Cloud SDK for Python that consumes an OData EDMX metadata file and produces a fully-typed, SDK-idiomatic Python client for that service. Generated code should be indistinguishable in style from hand-written SDK modules and should integrate with the existing destination, telemetry, and secret-resolver infrastructure.

---

## Motivation

Several BTP services already consumed by the SDK (DMS, ADMS) speak OData v4. Today each module hand-writes its own HTTP layer, query logic, and model classes, duplicating effort and diverging in quality. A generator would:

- Remove boilerplate for every new OData-backed service.
- Guarantee consistency with SDK conventions (naming, telemetry, exceptions, typing).
- Enable external consumers to generate clients for their own OData services.
- Align the Python SDK with the mature generation story already present in `cloud-sdk-java`.

---

## Scope

| In scope | Out of scope |
|---|---|
| OData v4 EDMX metadata parsing | OData v2 (defer to later iteration) |
| Entity CRUD (GetAll, GetByKey, Create, Update, Delete) | OData actions / functions (phase 2) |
| `$filter`, `$select`, `$orderby`, `$top`, `$skip`, `$expand` | Batch requests (phase 2) |
| Type-safe filter/select expression builders | Complex / derived types (phase 2) |
| Destination integration | Arbitrary HTTP transport plug-ins |
| Telemetry decorator wiring | Custom authentication beyond OAuth2 CC |
| CLI entrypoint + Claude Code skill | GUI or web-based generators |
| `uv`-runnable one-shot script | IDE plugins |

---

## Delivery Mechanisms

The generator must be reachable through multiple entry points so different personas can use it in the way that suits them.

### 1. CLI (primary)

A `sap-cloud-sdk-generate` command installed as part of the package:

```bash
# Minimal usage
uv run sap-cloud-sdk-generate odata \
    --input  path/to/service.edmx \
    --output src/sap_cloud_sdk/my_service/ \
    --package sap_cloud_sdk.my_service

# With all options
uv run sap-cloud-sdk-generate odata \
    --input   path/to/service.edmx \
    --output  src/sap_cloud_sdk/my_service/ \
    --package sap_cloud_sdk.my_service \
    --service-name MyService \
    --module-name  my_service \
    --async        \        # emit async client variant
    --overwrite            # allow overwriting existing files
```

Built with [Typer](https://typer.tiangolo.com/) (already philosophically aligned with Pydantic, zero heavyweight framework dependency). Exposed via `pyproject.toml`:

```toml
[project.scripts]
sap-cloud-sdk-generate = "sap_cloud_sdk.generator.cli:app"
```

### 2. Claude Code skill (`/generate-odata`)

A `scaffold-odata` skill definition committed to `.claude/skills/`:

```
/generate-odata --input <edmx-path> [--output <dir>] [--async]
```

The skill calls the same CLI under the hood via `Bash`, then optionally runs `uv run ruff format` and `uv run ty check` on the output. This lets contributors generate a new service client inside an ongoing Claude Code session without leaving the editor context.

Usage example in a Claude Code session:

```
/generate-odata --input docs/specs/my_service.edmx --output src/sap_cloud_sdk/my_service/
```

The skill also invokes the existing `/scaffold-module` skill as a pre-step when the output directory does not yet exist, ensuring the standard layout (telemetry wiring, `__init__.py`, `exceptions.py`) is created before generated entity code is written into it.

### 3. Python API (programmatic)

For use inside build scripts, CI, or other tooling:

```python
from sap_cloud_sdk.generator import ODataGenerator, GeneratorConfig

config = GeneratorConfig(
    input_path=Path("service.edmx"),
    output_dir=Path("src/sap_cloud_sdk/my_service"),
    package_name="sap_cloud_sdk.my_service",
    emit_async=True,
)
ODataGenerator(config).generate()
```

### 4. Makefile target (convention)

Following the proto generation precedent in `auditlog_ng`:

```makefile
generate-odata:
    uv run sap-cloud-sdk-generate odata \
        --input  $(SPEC_DIR)/$(SERVICE).edmx \
        --output src/sap_cloud_sdk/$(SERVICE)/ \
        --package sap_cloud_sdk.$(SERVICE)
```

---

## Architecture

```
src/sap_cloud_sdk/generator/
├── __init__.py               # Public API: ODataGenerator, GeneratorConfig
├── cli.py                    # Typer app, command definitions
├── _edmx_parser.py           # EDMX → internal IR (EntityType, Property, NavProp, ...)
├── _ir.py                    # Intermediate Representation dataclasses
├── _codegen.py               # IR → Python source (uses ast / string templates)
├── _template_renderer.py     # Jinja2 template rendering
├── _type_mapper.py           # Edm.* types → Python/Pydantic types
└── templates/
    ├── entity.py.jinja2       # Entity model class
    ├── request_builder.py.jinja2  # CRUD request builders
    ├── client.py.jinja2       # Service client facade
    ├── config.py.jinja2       # Config dataclass
    ├── exceptions.py.jinja2   # Module exceptions
    └── __init__.py.jinja2     # Public API exports
```

### Processing pipeline

```
EDMX file
   │
   ▼
_edmx_parser.py          (xml.etree.ElementTree or lxml)
   │  Edm types, EntityTypes, EntitySets, NavigationProperties
   ▼
_ir.py                   (ServiceModel, EntityModel, PropertyModel, ...)
   │
   ├──► _type_mapper.py  (Edm.String→str, Edm.DateTime→datetime, ...)
   │
   ▼
_template_renderer.py    (Jinja2 renders each template with IR data)
   │
   ▼
Generated Python files   (entity.py, request_builder.py, client.py, ...)
   │
   ▼
Post-processing          (ruff format, optional ty check)
```

---

## Generated Code Shape

Given an EDMX `EntityType` named `BusinessPartner` with properties `BusinessPartnerID (Edm.String, key)`, `DisplayName (Edm.String)`, `CreatedAt (Edm.DateTimeOffset)`, the generator produces:

### `_models.py` (entity)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

@dataclass
class BusinessPartner:
    """OData entity: BusinessPartner."""

    _entity_set: ClassVar[str] = "BusinessPartners"
    _key_fields: ClassVar[tuple[str, ...]] = ("business_partner_id",)

    business_partner_id: str
    display_name: str | None = None
    created_at: datetime | None = None
```

### `_request_builder.py` (CRUD helpers)

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from ._models import BusinessPartner
from ..odata import (
    GetAllRequestBuilder,
    GetByKeyRequestBuilder,
    CreateRequestBuilder,
    UpdateRequestBuilder,
    DeleteRequestBuilder,
)

if TYPE_CHECKING:
    from .client import BusinessPartnerServiceClient


class BusinessPartnerRequestBuilder:
    def __init__(self, client: BusinessPartnerServiceClient) -> None:
        self._client = client

    def get_all(self) -> GetAllRequestBuilder[BusinessPartner]:
        return GetAllRequestBuilder(self._client, BusinessPartner)

    def get_by_key(self, business_partner_id: str) -> GetByKeyRequestBuilder[BusinessPartner]:
        return GetByKeyRequestBuilder(
            self._client, BusinessPartner, {"BusinessPartnerID": business_partner_id}
        )

    def create(self, entity: BusinessPartner) -> CreateRequestBuilder[BusinessPartner]:
        return CreateRequestBuilder(self._client, entity)

    def update(self, entity: BusinessPartner) -> UpdateRequestBuilder[BusinessPartner]:
        return UpdateRequestBuilder(self._client, entity)

    def delete(self, business_partner_id: str) -> DeleteRequestBuilder[BusinessPartner]:
        return DeleteRequestBuilder(
            self._client, BusinessPartner, {"BusinessPartnerID": business_partner_id}
        )
```

### `client.py` (service facade)

```python
from __future__ import annotations
from typing import Optional
from sap_cloud_sdk.core.telemetry import Module, record_metrics
from ..odata import ODataHttpTransport
from .config import BusinessPartnerServiceConfig
from ._request_builder import BusinessPartnerRequestBuilder


class BusinessPartnerServiceClient:
    """Client for the BusinessPartner OData service."""

    def __init__(
        self,
        transport: ODataHttpTransport,
        config: BusinessPartnerServiceConfig,
        _telemetry_source: Optional[Module] = None,
    ) -> None:
        self._transport = transport
        self._config = config
        self._telemetry_source = _telemetry_source
        self.business_partners = BusinessPartnerRequestBuilder(self)

    @record_metrics(Module.BUSINESS_PARTNER_SERVICE, Operation.GET_ALL)
    def get_business_partners(self):
        return self.business_partners.get_all().execute()
```

---

## Type Mapping

| Edm type | Python type |
|---|---|
| `Edm.String` | `str` |
| `Edm.Int16` / `Edm.Int32` / `Edm.Int64` | `int` |
| `Edm.Decimal` / `Edm.Double` / `Edm.Single` | `float` |
| `Edm.Boolean` | `bool` |
| `Edm.DateTimeOffset` / `Edm.DateTime` | `datetime` |
| `Edm.Date` | `date` |
| `Edm.TimeOfDay` | `time` |
| `Edm.Binary` | `bytes` |
| `Edm.Guid` | `uuid.UUID` |
| Complex / Enum types | Generated nested `@dataclass` / `Enum` |

---

## Integration with Existing SDK

- **Destination**: `create_client()` factory accepts a `Destination` object; the `ODataHttpTransport` (from the shared abstractions module) is constructed from it.
- **Secret resolver**: `config.py` is generated with the same `read_from_mount_and_fallback_to_env_var` pattern used in all other modules.
- **Telemetry**: `Module` and `Operation` constants are generated; `@record_metrics` is applied to all client methods. The generator adds placeholders to `core/telemetry/module.py` and `core/telemetry/operation.py`.
- **Exceptions**: `exceptions.py` is generated extending `ODataError` (from the shared abstractions module) rather than base Python exceptions.
- **Async**: When `--async` is passed, an `AsyncBusinessPartnerServiceClient` variant is also emitted, wrapping `AsyncODataHttpTransport`.

---

## Dependencies

New generator dependencies (added under `[project.optional-dependencies]` as `[generator]`):

```toml
[project.optional-dependencies]
generator = [
    "typer>=0.12",
    "jinja2>=3.1",
    "lxml>=5.0",        # robust XML/EDMX parsing
]
```

Runtime (the generated clients themselves) depends only on the shared `odata` abstractions module — no extra runtime dependency for consumers.

---

## Quality Gates

Generated code must pass the same gates as hand-written code:

1. `uv run ruff format` — formatting (run automatically post-generation)
2. `uv run ruff check` — linting
3. `uv run ty check` — type checking
4. `uv run pytest tests/generator/` — generator unit tests (snapshot tests comparing generated output against golden files for sample EDMX specs)

---

## Testing Strategy

| Layer | Approach |
|---|---|
| EDMX parser | Unit tests with fixture `.edmx` files covering all Edm types |
| IR construction | Unit tests asserting correct `ServiceModel` shape |
| Template rendering | Snapshot tests: render template with known IR, diff against golden `.py` files |
| End-to-end generation | Run generator on `sample.edmx`, then run `ty check` and `ruff check` on output |
| CLI | Typer's `CliRunner` for command invocation tests |
| Generated client | Integration tests using a mock OData server (or VCR cassettes) |

---

## Phasing

### Phase 1 — Core generator
- EDMX parser + IR
- Entity model generation
- CRUD request builders (relies on shared OData abstractions — see companion proposal)
- Service client facade
- `create_client()` factory with destination integration
- CLI entrypoint
- Snapshot test suite

### Phase 2 — Advanced features
- OData actions and function imports
- Navigation property expansion helpers
- Batch request support
- Complex / derived type support
- OData v2 support

### Phase 3 — Developer experience
- Claude Code `/generate-odata` skill
- `--watch` mode (regenerate on EDMX change)
- VS Code extension hook (optional)

---

## Open Questions

1. **Jinja2 vs `ast` module**: Jinja2 templates are easier to maintain but harder to guarantee syntactic correctness. The `ast` module approach is verbose but produces provably valid Python. Recommendation: start with Jinja2 and validate output with `ast.parse()` as a post-step.
2. **Telemetry module constants**: Should the generator auto-append to `core/telemetry/module.py`, or emit a separate file and require manual merge? Auto-append is more ergonomic but modifies SDK-core files.
3. **Versioning generated code**: Should generated files carry a header comment with the generator version and source EDMX hash for drift detection?
4. **Conflict with existing DMS/ADMS modules**: Once the shared `odata` abstractions land, should DMS and ADMS be migrated to generated clients, or kept hand-written?
