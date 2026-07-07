import logging
from collections.abc import MutableMapping
from typing import Any, Callable, Dict, Optional, cast

from opentelemetry.baggage import get_all as get_all_baggage
from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.trace import Span
from opentelemetry.util.types import AttributeValue

logger = logging.getLogger(__name__)

BaggageKeyPredicateT = Callable[[str], bool]
ALLOW_ALL_BAGGAGE_KEYS: BaggageKeyPredicateT = lambda _: True  # noqa: E731

# Baggage keys where the caller-supplied value must win over any value set by
# framework callbacks after on_start
_DEFAULT_OVERRIDE_KEYS: tuple[str, ...] = ("gen_ai.conversation.id",)


class BaggageSpanProcessor(SpanProcessor):
    """Copies W3C baggage entries onto every span and enforces override keys.

    On ``on_start``: iterates all baggage entries, applies those matching
    ``baggage_key_predicate`` to the span via ``set_attribute``, and snapshots
    any ``override_keys`` values for re-application at end time.

    On ``on_end``: re-writes the snapshot override values directly into
    ``span._attributes``, ensuring they survive any framework ``set_attribute``
    calls made during the span's lifetime.

    Args:
        baggage_key_predicate: Called for each baggage key; attribute is copied
            only when this returns ``True``.  Use ``ALLOW_ALL_BAGGAGE_KEYS`` to
            copy everything.
        override_keys: Baggage keys whose value must always win over
            framework-injected span attributes.  Only keys actually present in
            baggage at span start are tracked.
    """

    def __init__(
        self,
        baggage_key_predicate: BaggageKeyPredicateT,
        override_keys: tuple[str, ...] = _DEFAULT_OVERRIDE_KEYS,
    ) -> None:
        self._baggage_key_predicate = baggage_key_predicate
        self._override_keys = frozenset(override_keys)
        self._pending: Dict[int, Dict[str, AttributeValue]] = {}

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        if not span.is_recording():
            return
        all_baggage = get_all_baggage(parent_context)
        for key, value in all_baggage.items():
            if self._baggage_key_predicate(key):
                span.set_attribute(key, cast(AttributeValue, value))

        overrides = {
            k: cast(AttributeValue, all_baggage[k])
            for k in self._override_keys
            if k in all_baggage
        }
        if overrides:
            span_id = getattr(getattr(span, "context", None), "span_id", None)
            if span_id is not None:
                self._pending[span_id] = overrides

    def on_end(self, span: ReadableSpan) -> None:
        span_id = getattr(getattr(span, "context", None), "span_id", None)
        if span_id is None:
            return
        overrides = self._pending.pop(span_id, None)
        if not overrides:
            return
        if not hasattr(span, "_attributes") or span._attributes is None:
            return
        try:
            cast(MutableMapping[str, Any], span._attributes).update(overrides)
        except Exception as exc:
            logger.debug(
                "BaggageSpanProcessor: error enforcing overrides on span %r: %s",
                getattr(span, "name", "<unknown>"),
                exc,
            )

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
