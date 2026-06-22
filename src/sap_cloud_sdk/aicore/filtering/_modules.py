"""Direction containers and top-level configuration for content filtering."""

from __future__ import annotations

from sap_cloud_sdk.core.env import read_env_bool, read_env_choice, read_env_str

from ._filters import AzureContentFilter, ContentFilter, Severity

_VALID_SEVERITIES: set[int] = {s.value for s in Severity}


class InputFiltering:
    """Input-direction filter stack.

    Args:
        filters: Ordered list of ``ContentFilter`` instances. The server applies
            them in order; the first to reject wins.
    """

    def __init__(self, filters: list[ContentFilter]) -> None:
        self.filters = filters

    def to_dict(self) -> dict:
        return {"filters": [f.to_dict() for f in self.filters]}


class OutputFiltering:
    """Output-direction filter stack.

    Args:
        filters: Ordered list of ``ContentFilter`` instances.
        stream_options: Optional module-specific streaming options. Passed
            through verbatim when set; omitted from the wire payload when
            ``None``.
    """

    def __init__(
        self,
        filters: list[ContentFilter],
        stream_options: dict | None = None,
    ) -> None:
        self.filters = filters
        self.stream_options = stream_options

    def to_dict(self) -> dict:
        result: dict = {"filters": [f.to_dict() for f in self.filters]}
        if self.stream_options:
            result["stream_options"] = self.stream_options
        return result


class ContentFiltering:
    """Complete content-filtering configuration for a single set_filtering call.

    Args:
        input_filtering: Filters applied to the user prompt before the model sees it.
        output_filtering: Filters applied to the model response before the user sees it.

    A direction key is omitted from the wire payload when its corresponding
    argument is ``None``.
    """

    def __init__(
        self,
        input_filtering: InputFiltering | None = None,
        output_filtering: OutputFiltering | None = None,
    ) -> None:
        self.input_filtering = input_filtering
        self.output_filtering = output_filtering

    def to_dict(self) -> dict:
        result: dict = {}
        if self.input_filtering is not None:
            result["input"] = self.input_filtering.to_dict()
        if self.output_filtering is not None:
            result["output"] = self.output_filtering.to_dict()
        return result

    @classmethod
    def from_env(cls) -> "ContentFiltering | None":
        """Build from ``AICORE_FILTER_*`` environment variables.

        Returns ``None`` when ``AICORE_FILTER_ENABLED=false``, disabling
        filtering entirely. Constructs a single ``AzureContentFilter`` per
        direction (LlamaGuard is opt-in via explicit programmatic config).

        Reads:
            AICORE_FILTER_ENABLED       (bool, default true)
            AICORE_FILTER_DIRECTIONS    (comma list, default "input,output")
            AICORE_FILTER_HATE          (int 0/2/4/6, default 4)
            AICORE_FILTER_VIOLENCE      (int 0/2/4/6, default 4)
            AICORE_FILTER_SEXUAL        (int 0/2/4/6, default 4)
            AICORE_FILTER_SELF_HARM     (int 0/2/4/6, default 4)
            AICORE_FILTER_PROMPT_SHIELD (bool, default true) — input-only
        """
        if not read_env_bool("AICORE_FILTER_ENABLED", default=True):
            return None

        directions_raw = read_env_str("AICORE_FILTER_DIRECTIONS", "input,output")
        directions = {d.strip() for d in directions_raw.split(",") if d.strip()}

        hate = Severity(
            read_env_choice("AICORE_FILTER_HATE", _VALID_SEVERITIES, default=4)
        )
        violence = Severity(
            read_env_choice("AICORE_FILTER_VIOLENCE", _VALID_SEVERITIES, default=4)
        )
        sexual = Severity(
            read_env_choice("AICORE_FILTER_SEXUAL", _VALID_SEVERITIES, default=4)
        )
        self_harm = Severity(
            read_env_choice("AICORE_FILTER_SELF_HARM", _VALID_SEVERITIES, default=4)
        )
        prompt_shield = read_env_bool("AICORE_FILTER_PROMPT_SHIELD", default=True)

        input_filtering: InputFiltering | None = None
        if "input" in directions:
            input_filtering = InputFiltering(
                filters=[
                    AzureContentFilter(
                        hate=hate,
                        violence=violence,
                        sexual=sexual,
                        self_harm=self_harm,
                        prompt_shield=prompt_shield,
                    )
                ]
            )

        output_filtering: OutputFiltering | None = None
        if "output" in directions:
            output_filtering = OutputFiltering(
                filters=[
                    AzureContentFilter(
                        hate=hate,
                        violence=violence,
                        sexual=sexual,
                        self_harm=self_harm,
                    )
                ]
            )

        return cls(
            input_filtering=input_filtering,
            output_filtering=output_filtering,
        )
