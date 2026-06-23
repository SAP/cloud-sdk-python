"""Zero-config IAS telemetry instrumentation for Starlette and FastAPI.

Patches ``starlette.applications.Starlette`` via class substitution so that
any app created after ``auto_instrument()`` automatically gets the IAS JWT
middleware — no ``app=`` reference required from the user.

Composes safely with the OpenTelemetry Kubernetes operator: whichever patch
runs first becomes the base class of the other, so both ``add_middleware``
calls fire via ``super().__init__()`` regardless of ordering.
"""

import logging
from contextvars import ContextVar
from typing import Any, Dict

from sap_cloud_sdk.core.telemetry.middleware.base import FrameworkInstrumentor
from sap_cloud_sdk.core.telemetry.middleware.registry import register

logger = logging.getLogger(__name__)

_attrs_var: ContextVar[Dict[str, Any]] = ContextVar("_sap_ias_attrs", default={})


@register
class StarletteIASInstrumentor(FrameworkInstrumentor):
    """Instruments Starlette and FastAPI with IAS JWT telemetry middleware.

    FastAPI subclasses Starlette and calls ``super().__init__()``, so patching
    ``starlette.applications.Starlette`` covers both frameworks with one patch.
    """

    _original: Any = None
    framework_key = "starlette"

    @classmethod
    def is_available(cls) -> bool:
        try:
            import starlette  # noqa: F401
            return True
        except ImportError:
            return False

    def _do_instrument(self) -> None:
        from starlette import applications
        from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import _IASMiddleware

        original = applications.Starlette

        class _SAPInstrumented(original):  # type: ignore[valid-type]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, **kwargs)
                if not getattr(self, "_sap_ias_done", False):
                    self._sap_ias_done = True
                    self.add_middleware(_IASMiddleware, attrs_var=_attrs_var)

        StarletteIASInstrumentor._original = original
        applications.Starlette = _SAPInstrumented

    def _do_uninstrument(self) -> None:
        if StarletteIASInstrumentor._original is None:
            return
        from starlette import applications
        applications.Starlette = StarletteIASInstrumentor._original
        StarletteIASInstrumentor._original = None

    def get_attributes(self) -> Dict[str, Any]:
        return _attrs_var.get()
