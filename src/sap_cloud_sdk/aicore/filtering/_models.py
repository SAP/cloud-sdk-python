"""Severity enum for SAP AI Core Orchestration v2 content filtering.

Other content-filtering types have moved:
- ContentFilter / AzureContentFilter / LlamaGuard38bFilter → :mod:`._filters`
- InputFiltering / OutputFiltering / ContentFiltering → :mod:`._modules`
"""

from __future__ import annotations

from enum import IntEnum


class Severity(IntEnum):
    """Azure Content Safety severity threshold for filter rejection.

    Lower values are stricter. ``STRICT`` blocks any detected content;
    ``OFF`` disables the filter. ``IntEnum`` so members serialise as their
    int value (``json.dumps(Severity.MEDIUM) == "4"``) — the wire format
    is unchanged from the previous ``Literal[0, 2, 4, 6]`` typing.
    """

    STRICT = 0
    LOW = 2
    MEDIUM = 4
    OFF = 6
