"""OData query option classes for ADMS — removed.

These classes (ConfigQueryOptions, RelationQueryOptions, DocumentQueryOptions)
have been removed. Use :class:`~sap_cloud_sdk.core.odata.StructuredQuery` directly::

    from sap_cloud_sdk.adms import create_client, StructuredQuery
    from sap_cloud_sdk.core.odata import FilterExpression

    client = create_client()
    client.relations.get_all(
        StructuredQuery().filter(FilterExpression.field("Name").eq("x")).top(10)
    )
"""
