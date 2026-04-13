from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor
FIELD_OPTIONS_FIELD_NUMBER: _ClassVar[int]
field_options: _descriptor.FieldDescriptor

class FieldOptions(_message.Message):
    __slots__ = ("ignore", "required", "min_length", "max_length", "pattern")
    IGNORE_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_FIELD_NUMBER: _ClassVar[int]
    MIN_LENGTH_FIELD_NUMBER: _ClassVar[int]
    MAX_LENGTH_FIELD_NUMBER: _ClassVar[int]
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    ignore: bool
    required: bool
    min_length: int
    max_length: int
    pattern: str
    def __init__(self, ignore: _Optional[bool] = ..., required: _Optional[bool] = ..., min_length: _Optional[int] = ..., max_length: _Optional[int] = ..., pattern: _Optional[str] = ...) -> None: ...
