"""OData query option classes for ADMS list/get-all operations.

These classes encapsulate the OData V4 query parameters accepted by the ADMS
list endpoints, mirroring the pattern established by ``ListOptions`` in the
destination module
(:mod:`sap_cloud_sdk.destination._models`).

The capability tiers nest strictly — Configuration endpoints accept the
smallest subset, DocumentRelation adds ``$select`` / ``$expand``, and Document
adds ``$orderby`` on top of that.  Modelling the tiers via inheritance lets
the type system reject calls that pass an unsupported field to the wrong
endpoint::

    client.documents.get_all(DocumentQueryOptions(orderby="..."))   # OK
    client.relations.get_all(DocumentQueryOptions(orderby="..."))   # also OK — DocumentQueryOptions ⊂ RelationQueryOptions accepts a superset
    client.configuration.get_all_allowed_domains(
        ConfigQueryOptions(filter="...")                            # OK
    )

Each ``to_query_params()`` returns a dict ready to drop into the HTTP layer's
``params=`` argument; ``None`` fields are omitted so the resulting URL stays
clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ConfigQueryOptions:
    """OData query options for ADMS Configuration list endpoints.

    Supports the minimal ``$filter`` / ``$top`` / ``$skip`` subset honoured
    by ``AllowedDomain``, ``DocumentType``, ``BusinessObjectNodeType``, and
    ``DocumentTypeBusinessObjectTypeMap`` entity sets.

    Attributes:
        filter: OData ``$filter`` expression.
        top: ``$top`` — maximum number of records to return.
        skip: ``$skip`` — number of records to skip (paging).
    """

    filter: Optional[str] = None
    top: Optional[int] = None
    skip: Optional[int] = None

    def to_query_params(self) -> dict[str, str | int]:
        """Convert this options object into an OData query-parameter dict.

        ``None`` fields are omitted entirely so the resulting URL contains
        only the parameters the caller actually set.
        """
        params: dict[str, str | int] = {}
        if self.filter is not None:
            params["$filter"] = self.filter
        if self.top is not None:
            params["$top"] = self.top
        if self.skip is not None:
            params["$skip"] = self.skip
        return params


@dataclass
class RelationQueryOptions(ConfigQueryOptions):
    """OData query options for the ``DocumentRelation`` list endpoint.

    Adds ``$select`` and ``$expand`` on top of :class:`ConfigQueryOptions`.

    .. note::
        ``$orderby`` is **not** supported by the ``DocumentRelation`` entity
        set — use :class:`DocumentQueryOptions` if you need it for the
        ``Document`` entity set.

    Attributes:
        select: Properties to include in the response (``$select``).
        expand: Navigation properties to inline (``$expand``).
    """

    select: Optional[list[str]] = None
    expand: Optional[list[str]] = None

    def to_query_params(self) -> dict[str, str | int]:
        params = super().to_query_params()
        if self.select is not None:
            params["$select"] = ",".join(self.select)
        if self.expand is not None:
            params["$expand"] = ",".join(self.expand)
        return params


@dataclass
class DocumentQueryOptions(RelationQueryOptions):
    """OData query options for the ``Document`` list endpoint.

    Adds ``$orderby`` on top of :class:`RelationQueryOptions` — the full
    OData V4 query surface exposed by the ``Document`` entity set.

    Attributes:
        orderby: OData ``$orderby`` expression (e.g. ``"CreatedAt desc"``).
    """

    orderby: Optional[str] = None

    def to_query_params(self) -> dict[str, str | int]:
        params = super().to_query_params()
        if self.orderby is not None:
            params["$orderby"] = self.orderby
        return params
