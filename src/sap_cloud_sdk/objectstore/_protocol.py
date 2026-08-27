"""Protocol definition for object store clients."""

from types import TracebackType
from typing import BinaryIO, List, Protocol, Self, runtime_checkable

from sap_cloud_sdk.objectstore._models import ObjectMetadata


class ObjectReader(Protocol):
    """Managed binary reader returned by an object store backend."""

    def read(self, size: int = -1, /) -> bytes: ...

    def close(self) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None: ...


@runtime_checkable
class ObjectStoreClient(Protocol):
    """Protocol defining the object store client interface.

    All provider backends satisfy this protocol.
    Use ``create_client()`` to obtain a concrete implementation.
    """

    def put_object_from_bytes(
        self, name: str, data: bytes, content_type: str
    ) -> None: ...

    def put_object(
        self, name: str, stream: BinaryIO, size: int, content_type: str
    ) -> None: ...

    def put_object_from_file(
        self, name: str, file_path: str, content_type: str
    ) -> None: ...

    def get_object(self, name: str) -> ObjectReader: ...

    def delete_object(self, name: str) -> None: ...

    def list_objects(self, prefix: str) -> List[ObjectMetadata]: ...

    def head_object(self, name: str) -> ObjectMetadata: ...

    def object_exists(self, name: str) -> bool: ...
