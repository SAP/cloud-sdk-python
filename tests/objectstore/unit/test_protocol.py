"""Static contract examples for the object store protocols."""

from sap_cloud_sdk.objectstore import ObjectStoreClient


def _read_object_with_managed_lifecycle(client: ObjectStoreClient) -> bytes:
    """Exercise the public reader contract for static type checking."""
    with client.get_object("object.bin") as reader:
        return reader.read()


def _close_object_reader_explicitly(client: ObjectStoreClient) -> None:
    """Ensure explicit cleanup is also part of the public contract."""
    reader = client.get_object("object.bin")
    reader.close()
