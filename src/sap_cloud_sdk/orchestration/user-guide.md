# Orchestration — Content Filtering & Prompt Shield

This module activates Azure Content Safety filtering and prompt attack detection
for all SAP AI Core model calls. It is part of `sap-cloud-sdk` and requires no
separate installation.

## Getting started

**No code change is required.** Filtering is automatically activated when
`set_aicore_config()` is called. Every subsequent `sap/*` model call through
LiteLLM is filtered.

```python
from sap_cloud_sdk.aicore import set_aicore_config

set_aicore_config()
# ← filtering active at threshold 4/4/4/4 + prompt_shield=True
```

## Default policy

| Category | Default threshold | Meaning |
|---|---|---|
| Hate | 4 | Block medium+ severity |
| Violence | 4 | Block medium+ severity |
| Sexual | 4 | Block medium+ severity |
| Self-harm | 4 | Block medium+ severity |
| Prompt shield | enabled | Block jailbreak + indirect injection attempts (input-only) |

Severity scale: `0` = strict (block any detected content), `2` = low+, `4` = medium+ (default), `6` = off.

## Configuration via environment variables

Set these before calling `set_aicore_config()`:

| Variable | Default | Description |
|---|---|---|
| `ORCH_FILTER_ENABLED` | `true` | Set `false` to disable filtering entirely |
| `ORCH_FILTER_DIRECTIONS` | `input,output` | Comma-list: `input`, `output`, or both |
| `ORCH_FILTER_HATE` | `4` | Azure severity threshold (0/2/4/6) |
| `ORCH_FILTER_VIOLENCE` | `4` | Azure severity threshold |
| `ORCH_FILTER_SEXUAL` | `4` | Azure severity threshold |
| `ORCH_FILTER_SELF_HARM` | `4` | Azure severity threshold |
| `ORCH_FILTER_PROMPT_SHIELD` | `true` | Enable/disable prompt shield |

Example — tighten self-harm and violence:
```bash
ORCH_FILTER_SELF_HARM=0
ORCH_FILTER_VIOLENCE=0
```

## Programmatic override with `set_filtering()`

Only needed to override thresholds at runtime. Call after `set_aicore_config()`.

```python
from sap_cloud_sdk.orchestration import set_filtering

# Tighten specific thresholds
set_filtering(self_harm=0, violence=0)

# Disable filtering entirely
set_filtering(enabled=False)
```

`set_filtering()` arguments:

| Argument | Type | Description |
|---|---|---|
| `hate` | `0\|2\|4\|6` | Override hate threshold |
| `violence` | `0\|2\|4\|6` | Override violence threshold |
| `sexual` | `0\|2\|4\|6` | Override sexual threshold |
| `self_harm` | `0\|2\|4\|6` | Override self-harm threshold |
| `prompt_shield` | `bool` | Enable/disable prompt shield |
| `directions` | `set[str]` | Override active directions |
| `enabled` | `bool` | `False` disables filtering entirely |

Unspecified arguments retain their current values (from env or defaults).

## Handling blocked requests

When the filter rejects a request, LiteLLM raises either a `ContentFilteredError`
(if the rejection reaches `transform_response`) or an `APIConnectionError` wrapping
the rejection JSON (for input-filter 400s caught by `raise_for_status()`). Use
`extract_filter_blocked()` for the second case.

```python
from sap_cloud_sdk.orchestration import ContentFilteredError
from sap_cloud_sdk.orchestration._litellm_patch import extract_filter_blocked

try:
    result = await llm.ainvoke(messages)
except ContentFilteredError as e:
    # e.direction: "input" or "output"
    # e.details: severity scores (safe to log — does not contain the prompt)
    # e.request_id: for debugging
    return "Your request was blocked by content safety policy."
except Exception as e:
    blocked = extract_filter_blocked(e)   # unwraps LiteLLM-wrapped 400
    if blocked:
        return "Your request was blocked by content safety policy."
    raise
```

## Disabling filtering

Via environment variable (before `set_aicore_config()`):
```bash
ORCH_FILTER_ENABLED=false
```

Programmatically (after `set_aicore_config()`):
```python
set_filtering(enabled=False)
```

## Migration from manual `litellm_extension.py`

If your agent implements content filtering manually (e.g. by subclassing
`GenAIHubOrchestrationConfig`), you can replace the entire implementation
with the SDK:

```python
# Before (manual):
from orchestration.litellm_extension import install
install()

# After (SDK):
# Nothing — set_aicore_config() activates filtering automatically.
# Remove the manual install() call and the local litellm_extension.py module.
```

To use the SDK's types in your agent for catching filter exceptions:
```python
# Replace:
from orchestration.exceptions import ContentFilterBlocked
# With:
from sap_cloud_sdk.orchestration import ContentFilteredError
```

And `extract_filter_blocked`:
```python
# Replace:
from orchestration.litellm_extension import extract_filter_blocked
# With:
from sap_cloud_sdk.orchestration._litellm_patch import extract_filter_blocked
```
