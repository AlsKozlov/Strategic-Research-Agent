from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Outcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OUTCOME_UNSPECIFIED: _ClassVar[Outcome]
    OUTCOME_OK: _ClassVar[Outcome]
    OUTCOME_DENIED_SECURITY: _ClassVar[Outcome]
    OUTCOME_NONE_CLARIFICATION: _ClassVar[Outcome]
    OUTCOME_NONE_UNSUPPORTED: _ClassVar[Outcome]
    OUTCOME_ERR_INTERNAL: _ClassVar[Outcome]
OUTCOME_UNSPECIFIED: Outcome
OUTCOME_OK: Outcome
OUTCOME_DENIED_SECURITY: Outcome
OUTCOME_NONE_CLARIFICATION: Outcome
OUTCOME_NONE_UNSUPPORTED: Outcome
OUTCOME_ERR_INTERNAL: Outcome

class ReadRequest(_message.Message):
    __slots__ = ("path", "number", "start_line", "end_line")
    PATH_FIELD_NUMBER: _ClassVar[int]
    NUMBER_FIELD_NUMBER: _ClassVar[int]
    START_LINE_FIELD_NUMBER: _ClassVar[int]
    END_LINE_FIELD_NUMBER: _ClassVar[int]
    path: str
    number: bool
    start_line: int
    end_line: int
    def __init__(self, path: _Optional[str] = ..., number: bool = ..., start_line: _Optional[int] = ..., end_line: _Optional[int] = ...) -> None: ...

class ReadResponse(_message.Message):
    __slots__ = ("path", "content")
    PATH_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    path: str
    content: str
    def __init__(self, path: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

class WriteRequest(_message.Message):
    __slots__ = ("path", "content", "start_line", "end_line")
    PATH_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    START_LINE_FIELD_NUMBER: _ClassVar[int]
    END_LINE_FIELD_NUMBER: _ClassVar[int]
    path: str
    content: str
    start_line: int
    end_line: int
    def __init__(self, path: _Optional[str] = ..., content: _Optional[str] = ..., start_line: _Optional[int] = ..., end_line: _Optional[int] = ...) -> None: ...

class WriteResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DeleteRequest(_message.Message):
    __slots__ = ("path",)
    PATH_FIELD_NUMBER: _ClassVar[int]
    path: str
    def __init__(self, path: _Optional[str] = ...) -> None: ...

class DeleteResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class MkDirRequest(_message.Message):
    __slots__ = ("path",)
    PATH_FIELD_NUMBER: _ClassVar[int]
    path: str
    def __init__(self, path: _Optional[str] = ...) -> None: ...

class MkDirResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class MoveRequest(_message.Message):
    __slots__ = ("from_name", "to_name")
    FROM_NAME_FIELD_NUMBER: _ClassVar[int]
    TO_NAME_FIELD_NUMBER: _ClassVar[int]
    from_name: str
    to_name: str
    def __init__(self, from_name: _Optional[str] = ..., to_name: _Optional[str] = ...) -> None: ...

class MoveResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListRequest(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class ListResponse(_message.Message):
    __slots__ = ("entries",)
    class Entry(_message.Message):
        __slots__ = ("name", "is_dir")
        NAME_FIELD_NUMBER: _ClassVar[int]
        IS_DIR_FIELD_NUMBER: _ClassVar[int]
        name: str
        is_dir: bool
        def __init__(self, name: _Optional[str] = ..., is_dir: bool = ...) -> None: ...
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[ListResponse.Entry]
    def __init__(self, entries: _Optional[_Iterable[_Union[ListResponse.Entry, _Mapping]]] = ...) -> None: ...

class TreeRequest(_message.Message):
    __slots__ = ("root", "level")
    ROOT_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    root: str
    level: int
    def __init__(self, root: _Optional[str] = ..., level: _Optional[int] = ...) -> None: ...

class TreeResponse(_message.Message):
    __slots__ = ("root",)
    class Entry(_message.Message):
        __slots__ = ("name", "is_dir", "children")
        NAME_FIELD_NUMBER: _ClassVar[int]
        IS_DIR_FIELD_NUMBER: _ClassVar[int]
        CHILDREN_FIELD_NUMBER: _ClassVar[int]
        name: str
        is_dir: bool
        children: _containers.RepeatedCompositeFieldContainer[TreeResponse.Entry]
        def __init__(self, name: _Optional[str] = ..., is_dir: bool = ..., children: _Optional[_Iterable[_Union[TreeResponse.Entry, _Mapping]]] = ...) -> None: ...
    ROOT_FIELD_NUMBER: _ClassVar[int]
    root: TreeResponse.Entry
    def __init__(self, root: _Optional[_Union[TreeResponse.Entry, _Mapping]] = ...) -> None: ...

class FindRequest(_message.Message):
    __slots__ = ("root", "name", "type", "limit")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TYPE_ALL: _ClassVar[FindRequest.Type]
        TYPE_FILES: _ClassVar[FindRequest.Type]
        TYPE_DIRS: _ClassVar[FindRequest.Type]
    TYPE_ALL: FindRequest.Type
    TYPE_FILES: FindRequest.Type
    TYPE_DIRS: FindRequest.Type
    ROOT_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    root: str
    name: str
    type: FindRequest.Type
    limit: int
    def __init__(self, root: _Optional[str] = ..., name: _Optional[str] = ..., type: _Optional[_Union[FindRequest.Type, str]] = ..., limit: _Optional[int] = ...) -> None: ...

class FindResponse(_message.Message):
    __slots__ = ("items",)
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, items: _Optional[_Iterable[str]] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ("root", "pattern", "limit")
    ROOT_FIELD_NUMBER: _ClassVar[int]
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    root: str
    pattern: str
    limit: int
    def __init__(self, root: _Optional[str] = ..., pattern: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = ("matches",)
    class Match(_message.Message):
        __slots__ = ("path", "line", "line_text")
        PATH_FIELD_NUMBER: _ClassVar[int]
        LINE_FIELD_NUMBER: _ClassVar[int]
        LINE_TEXT_FIELD_NUMBER: _ClassVar[int]
        path: str
        line: int
        line_text: str
        def __init__(self, path: _Optional[str] = ..., line: _Optional[int] = ..., line_text: _Optional[str] = ...) -> None: ...
    MATCHES_FIELD_NUMBER: _ClassVar[int]
    matches: _containers.RepeatedCompositeFieldContainer[SearchResponse.Match]
    def __init__(self, matches: _Optional[_Iterable[_Union[SearchResponse.Match, _Mapping]]] = ...) -> None: ...

class ContextRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ContextResponse(_message.Message):
    __slots__ = ("unix_time", "time")
    UNIX_TIME_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    unix_time: int
    time: str
    def __init__(self, unix_time: _Optional[int] = ..., time: _Optional[str] = ...) -> None: ...

class AnswerRequest(_message.Message):
    __slots__ = ("message", "outcome", "refs")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    REFS_FIELD_NUMBER: _ClassVar[int]
    message: str
    outcome: Outcome
    refs: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, message: _Optional[str] = ..., outcome: _Optional[_Union[Outcome, str]] = ..., refs: _Optional[_Iterable[str]] = ...) -> None: ...

class AnswerResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
