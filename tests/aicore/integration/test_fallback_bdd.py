"""BDD step definitions for fallback integration tests.

Run against a live AI Core orchestration deployment:

    AICORE_CLIENT_ID=...  AICORE_CLIENT_SECRET=...  AICORE_AUTH_URL=... \\
    AICORE_BASE_URL=...   AICORE_RESOURCE_GROUP=... \\
    AICORE_FALLBACK_TEST_PRIMARY_MODEL=sap/unsupported-in-region \\
    AICORE_FALLBACK_TEST_FALLBACK_MODEL=sap/mistralai--mistral-small-instruct \\
    uv run python -m pytest tests/aicore/integration/test_fallback_bdd.py -v

The conftest skips fallback scenarios cleanly when the AICORE_FALLBACK_TEST_*
env vars are missing.

The "primary" model should be one that the orchestration server reports as
unsupported in the deployed region (the canonical way to force fallback
without relying on transient 5xx errors). The "fallback" must be a supported
model that the resource group can call.
"""

from __future__ import annotations

from typing import Any, Optional

import pytest
from pytest_bdd import given, scenarios, then, when

from sap_cloud_sdk.aicore import (
    ContentFilteredError,
    FallbackConfig,
    FallbackModel,
    completion,
    set_fallbacks,
    set_filtering,
)

scenarios("fallback.feature")


BENIGN_PROMPT = "Reply with 'ok' in English."


class ScenarioContext:
    """Per-scenario state."""

    def __init__(self) -> None:
        self.response: Any = None
        self.streamed_content: str = ""
        self.error: Optional[Exception] = None


@pytest.fixture
def ctx() -> ScenarioContext:
    return ScenarioContext()


# ---------------- Background ----------------


@given("AI Core credentials are configured")
def creds_configured():
    """Background — covered by the session-scoped fixture in conftest."""


@given("primary and fallback test models are configured")
def models_configured(fallback_models: tuple[str, str]):
    """Background — assert the fallback fixture resolved (else it skips)."""
    primary, fallback = fallback_models
    assert primary and fallback


# ---------------- Given (fallback / filtering state) ----------------


@given("fallback is disabled")
def fallback_off():
    set_fallbacks(None)


@given("fallback is configured with the test fallback model")
def fallback_on(fallback_models: tuple[str, str]):
    _primary, fallback = fallback_models
    set_fallbacks(FallbackConfig([FallbackModel(model=fallback)]))


@given("filtering is enabled with default thresholds")
def filtering_default():
    set_filtering()


# ---------------- When (send prompt) ----------------


def _capture_completion(ctx: ScenarioContext, model: str, prompt: str) -> None:
    """Send a non-streaming completion and capture the response or error.

    Uses ``sap_cloud_sdk.aicore.completion`` so that input- and output-filter
    rejections both surface as :class:`ContentFilteredError` — no wrapper
    unwrapping is needed here.
    """
    try:
        ctx.response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
    except ContentFilteredError as e:
        ctx.error = e
    except Exception as e:
        ctx.error = e


@when("I send a benign prompt to the fallback test model")
def send_to_fallback_model(ctx: ScenarioContext, fallback_models: tuple[str, str]):
    _primary, fallback = fallback_models
    _capture_completion(ctx, fallback, BENIGN_PROMPT)


@when("I send a benign prompt to the unsupported primary model")
def send_to_primary(ctx: ScenarioContext, fallback_models: tuple[str, str]):
    primary, _fallback = fallback_models
    _capture_completion(ctx, primary, BENIGN_PROMPT)


@when("I send a benign streaming prompt to the unsupported primary model")
def send_streaming_to_primary(ctx: ScenarioContext, fallback_models: tuple[str, str]):
    primary, _fallback = fallback_models
    try:
        stream = completion(
            model=primary,
            messages=[{"role": "user", "content": BENIGN_PROMPT}],
            stream=True,
        )
        parts: list[str] = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                parts.append(delta)
        ctx.streamed_content = "".join(parts)
    except Exception as e:
        ctx.error = e


# ---------------- Then (assertions) ----------------


@then("the response should contain a non-empty completion")
def response_non_empty(ctx: ScenarioContext):
    assert ctx.response is not None, f"no response (error={ctx.error})"
    content = ctx.response.choices[0].message.content
    assert isinstance(content, str) and content.strip(), (
        f"expected non-empty completion, got {content!r}"
    )


@then("the response has no intermediate_failures")
def no_intermediate_failures(ctx: ScenarioContext):
    assert ctx.response is not None
    assert getattr(ctx.response, "intermediate_failures", None) is None


@then("the response has a non-empty intermediate_failures list")
def has_intermediate_failures(ctx: ScenarioContext):
    assert ctx.response is not None
    failures = getattr(ctx.response, "intermediate_failures", None)
    assert failures, f"expected non-empty intermediate_failures, got {failures!r}"


@then("no ContentFilteredError is raised")
def no_filter_error(ctx: ScenarioContext):
    assert not isinstance(ctx.error, ContentFilteredError), (
        f"unexpected ContentFilteredError: {ctx.error}"
    )


@then("the streamed response should contain non-empty content")
def streamed_non_empty(ctx: ScenarioContext):
    assert ctx.error is None, f"streaming failed: {ctx.error}"
    assert ctx.streamed_content.strip(), (
        f"expected non-empty streamed content, got {ctx.streamed_content!r}"
    )
