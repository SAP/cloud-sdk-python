"""A2A card serialization helpers for the extensibility module.

Converts ``ExtensionCapability`` dataclasses into ``a2a-sdk``'s
``AgentExtension`` objects for inclusion in an agent's A2A card.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Dict, List

from a2a.types import AgentExtension

from sap_cloud_sdk.extensibility._models import ExtensionCapability, HookCapability

logger = logging.getLogger(__name__)

#: Schema version embedded in the extension capability URN.
#: Incremented when breaking changes are made to ExtensionCapability.
EXTENSION_CAPABILITY_SCHEMA_VERSION = 1

#: URN template for extension capability URIs.
_URN_TEMPLATE = "urn:sap:extension-capability:v{version}:{id}"


def _to_camel_case(snake_str: str) -> str:
    """Convert a snake_case string to camelCase.

    Args:
        snake_str: A snake_case string (e.g., ``"display_name"``).

    Returns:
        The camelCase equivalent (e.g., ``"displayName"``).
    """
    parts = snake_str.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def _tools_to_dict(tools: Any) -> Dict[str, Any]:
    """Serialize a ``Tools`` dataclass to a dict with camelCase keys.

    Recursively converts all nested dataclass fields (e.g. ``additions``)
    to dicts with camelCase keys, mirroring the A2A card wire format.

    Args:
        tools: A ``Tools`` instance.

    Returns:
        Dict with camelCase keys (e.g.,
        ``{"additions": {"enabled": True}}``).
    """
    raw = dataclasses.asdict(tools)
    return _snake_dict_to_camel(raw)


def _supported_hooks_to_dict(
    supported_hooks: List[HookCapability],
) -> List[Dict[str, Any]]:
    """Serialize a list of ``HookCapability`` dataclass to a list of dict with camelCase keys.

    Recursively converts all nested dataclass fields to dicts with camelCase keys, mirroring the A2A card wire format.

    Args:
        hooks: A list of ``HookCapability`` instances.

    Returns:
        List of dict with camelCase keys (e.g.,
        ``[{"type": "BEFORE", "id": "onboarding_before", "displayName": "Onboarding Before Hook", "description": "Hook executed before onboarding workflow step."}]``).
    """
    result = []
    for hook in supported_hooks:
        raw = dataclasses.asdict(hook)
        result.append(_snake_dict_to_camel(raw))
    return result


def _snake_dict_to_camel(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively convert a dict's keys from snake_case to camelCase.

    Args:
        d: Dict with snake_case keys, possibly nested.

    Returns:
        New dict with camelCase keys at all levels.
    """
    result: Dict[str, Any] = {}
    for k, v in d.items():
        camel_key = _to_camel_case(k)
        if isinstance(v, dict):
            result[camel_key] = _snake_dict_to_camel(v)
        else:
            result[camel_key] = v
    return result


def _validate_extension_capabilities(
    extension_capabilities: List[ExtensionCapability],
) -> None:
    """Validate extension capabilities and log warnings for issues.

    Checks for:
    - Empty extension capability lists
    - Duplicate extension capability IDs
    - Empty or whitespace-only IDs

    Warnings are logged rather than exceptions raised, following
    the extensibility module's convention of graceful degradation.

    Args:
        extension_capabilities: List of extension capabilities to validate.
    """
    if not extension_capabilities:
        logger.warning(
            "build_extension_capabilities() called with an empty list. "
            "No AgentExtension objects will be produced."
        )
        return

    seen_ids: Dict[str, int] = {}
    for i, cap in enumerate(extension_capabilities):
        if not cap.id or not cap.id.strip():
            logger.warning(
                "Extension capability at index %d has an empty or "
                "whitespace-only ID. This may cause issues with "
                "A2A card serialization.",
                i,
            )

        cap_id = cap.id
        if cap_id in seen_ids:
            logger.warning(
                "Duplicate extension capability ID %r found at "
                "indices %d and %d. Each extension capability should "
                "have a unique ID.",
                cap_id,
                seen_ids[cap_id],
                i,
            )
        else:
            seen_ids[cap_id] = i


def build_extension_capabilities(
    extension_capabilities: List[ExtensionCapability],
) -> List[AgentExtension]:
    """Convert extension capability definitions to A2A AgentExtension objects.

    Each ``ExtensionCapability`` is mapped to an ``AgentExtension`` with:

    - ``uri``: ``urn:sap:extension-capability:v{version}:{id}``
    - ``description``: From the capability's description field
    - ``params``: A dict with camelCase keys containing ``capabilityId``,
      ``displayName``, ``instructionSupported``, ``tools`` (serialized
      ``Tools`` and ``supportedHooks`` (serialized ``HookCapability``))
    - ``required``: Always ``False``

    Input (list of ExtensionCapability)::

        [{
            "id": "default",
            "display_name": "Default",
            "description": "Extension capability to further enhance agent.",
            "instruction_supported": True,
            "tools": Tools(additions=ToolAdditions(enabled=True)),
            "supported_hooks": [HookCapability(type="BEFORE", id="onboarding_before", display_name="Onboarding Before Hook", description="Hook executed before onboarding workflow step.")]
        }]

    Output (list of AgentExtension)::

        [{
            "uri": "urn:sap:extension-capability:v1:default",
            "description": "Extension capability to further enhance agent.",
            "params": {
                "capabilityId": "default",
                "displayName": "Default",
                "instructionSupported": True,
                "tools": {"additions": {"enabled": True}},
                "supportedHooks": [{"type": "BEFORE", "id": "onboarding_before", "displayName": "Onboarding Before Hook", "description": "Hook executed before onboarding workflow step."}]
            },
            "required": False
        }]

    Args:
        extension_capabilities: List of extension capabilities declared
            by the agent. Each entry must have: id, display_name,
            description, instruction_supported, and tools config.

    Returns:
        List of ``AgentExtension`` objects for inclusion in
        ``AgentCapabilities.extensions``. Each ``AgentExtension`` carries
        the URI, description, params (with camelCase keys), and
        ``required=False``.
    """
    _validate_extension_capabilities(extension_capabilities)

    result: List[AgentExtension] = []
    for cap in extension_capabilities:
        uri = _URN_TEMPLATE.format(
            version=EXTENSION_CAPABILITY_SCHEMA_VERSION,
            id=cap.id,
        )

        tools_dict = _tools_to_dict(cap.tools)
        supported_hooks_dict = _supported_hooks_to_dict(cap.supported_hooks)

        params: Dict[str, Any] = {
            "capabilityId": cap.id,
            "displayName": cap.display_name,
            "instructionSupported": cap.instruction_supported,
            "tools": tools_dict,
            "supportedHooks": supported_hooks_dict,
        }

        agent_extension = AgentExtension(
            uri=uri,
            description=cap.description,
            params=params,
            required=False,
        )
        result.append(agent_extension)

    return result
