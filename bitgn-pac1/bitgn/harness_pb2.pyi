from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EvalPolicy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EVAL_POLICY_UNSPECIFIED: _ClassVar[EvalPolicy]
    EVAL_POLICY_BLIND: _ClassVar[EvalPolicy]
    EVAL_POLICY_OPEN: _ClassVar[EvalPolicy]
    EVAL_POLICY_PRIVATE: _ClassVar[EvalPolicy]

class LinkKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LINK_KIND_UNSPECIFIED: _ClassVar[LinkKind]
    LINK_KIND_SAMPLE: _ClassVar[LinkKind]
    LINK_KIND_LANDING: _ClassVar[LinkKind]
    LINK_KIND_NEWS: _ClassVar[LinkKind]
    LINK_KIND_SDK: _ClassVar[LinkKind]

class TrialState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRIAL_STATE_UNSPECIFIED: _ClassVar[TrialState]
    TRIAL_STATE_NEW: _ClassVar[TrialState]
    TRIAL_STATE_RUNNING: _ClassVar[TrialState]
    TRIAL_STATE_DONE: _ClassVar[TrialState]
    TRIAL_STATE_ERROR: _ClassVar[TrialState]

class RunState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RUN_STATE_UNSPECIFIED: _ClassVar[RunState]
    RUN_STATE_RUNNING: _ClassVar[RunState]
    RUN_STATE_PENDING_EVAL: _ClassVar[RunState]
    RUN_STATE_EVALUATED: _ClassVar[RunState]

class LogKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LOG_KIND_UNSPECIFIED: _ClassVar[LogKind]
    LOG_KIND_SYSTEM: _ClassVar[LogKind]
    LOG_KIND_REQUEST: _ClassVar[LogKind]
    LOG_KIND_RESPONSE: _ClassVar[LogKind]
    LOG_KIND_ERROR: _ClassVar[LogKind]
    LOG_KIND_CHANGE: _ClassVar[LogKind]
    LOG_KIND_TELEMETRY: _ClassVar[LogKind]
    LOG_KIND_USER: _ClassVar[LogKind]
EVAL_POLICY_UNSPECIFIED: EvalPolicy
EVAL_POLICY_BLIND: EvalPolicy
EVAL_POLICY_OPEN: EvalPolicy
EVAL_POLICY_PRIVATE: EvalPolicy
LINK_KIND_UNSPECIFIED: LinkKind
LINK_KIND_SAMPLE: LinkKind
LINK_KIND_LANDING: LinkKind
LINK_KIND_NEWS: LinkKind
LINK_KIND_SDK: LinkKind
TRIAL_STATE_UNSPECIFIED: TrialState
TRIAL_STATE_NEW: TrialState
TRIAL_STATE_RUNNING: TrialState
TRIAL_STATE_DONE: TrialState
TRIAL_STATE_ERROR: TrialState
RUN_STATE_UNSPECIFIED: RunState
RUN_STATE_RUNNING: RunState
RUN_STATE_PENDING_EVAL: RunState
RUN_STATE_EVALUATED: RunState
LOG_KIND_UNSPECIFIED: LogKind
LOG_KIND_SYSTEM: LogKind
LOG_KIND_REQUEST: LogKind
LOG_KIND_RESPONSE: LogKind
LOG_KIND_ERROR: LogKind
LOG_KIND_CHANGE: LogKind
LOG_KIND_TELEMETRY: LogKind
LOG_KIND_USER: LogKind

class StatusRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class StatusResponse(_message.Message):
    __slots__ = ("status", "version")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    status: str
    version: str
    def __init__(self, status: _Optional[str] = ..., version: _Optional[str] = ...) -> None: ...

class GetBenchmarkRequest(_message.Message):
    __slots__ = ("benchmark_id",)
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    benchmark_id: str
    def __init__(self, benchmark_id: _Optional[str] = ...) -> None: ...

class Link(_message.Message):
    __slots__ = ("url", "kind")
    URL_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    url: str
    kind: LinkKind
    def __init__(self, url: _Optional[str] = ..., kind: _Optional[_Union[LinkKind, str]] = ...) -> None: ...

class GetBenchmarkResponse(_message.Message):
    __slots__ = ("benchmark_id", "description", "harness_id", "policy", "links", "tasks")
    class Task(_message.Message):
        __slots__ = ("task_id", "preview", "hint")
        TASK_ID_FIELD_NUMBER: _ClassVar[int]
        PREVIEW_FIELD_NUMBER: _ClassVar[int]
        HINT_FIELD_NUMBER: _ClassVar[int]
        task_id: str
        preview: str
        hint: str
        def __init__(self, task_id: _Optional[str] = ..., preview: _Optional[str] = ..., hint: _Optional[str] = ...) -> None: ...
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    HARNESS_ID_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    LINKS_FIELD_NUMBER: _ClassVar[int]
    TASKS_FIELD_NUMBER: _ClassVar[int]
    benchmark_id: str
    description: str
    harness_id: str
    policy: EvalPolicy
    links: _containers.RepeatedCompositeFieldContainer[Link]
    tasks: _containers.RepeatedCompositeFieldContainer[GetBenchmarkResponse.Task]
    def __init__(self, benchmark_id: _Optional[str] = ..., description: _Optional[str] = ..., harness_id: _Optional[str] = ..., policy: _Optional[_Union[EvalPolicy, str]] = ..., links: _Optional[_Iterable[_Union[Link, _Mapping]]] = ..., tasks: _Optional[_Iterable[_Union[GetBenchmarkResponse.Task, _Mapping]]] = ...) -> None: ...

class StartTrialRequest(_message.Message):
    __slots__ = ("trial_id",)
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    def __init__(self, trial_id: _Optional[str] = ...) -> None: ...

class StartTrialResponse(_message.Message):
    __slots__ = ("trial_id", "benchmark_id", "task_id", "run_id", "instruction", "harness_url")
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    HARNESS_URL_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    benchmark_id: str
    task_id: str
    run_id: str
    instruction: str
    harness_url: str
    def __init__(self, trial_id: _Optional[str] = ..., benchmark_id: _Optional[str] = ..., task_id: _Optional[str] = ..., run_id: _Optional[str] = ..., instruction: _Optional[str] = ..., harness_url: _Optional[str] = ...) -> None: ...

class StartPlaygroundResponse(_message.Message):
    __slots__ = ("trial_id", "benchmark_id", "task_id", "instruction", "harness_url")
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    HARNESS_URL_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    benchmark_id: str
    task_id: str
    instruction: str
    harness_url: str
    def __init__(self, trial_id: _Optional[str] = ..., benchmark_id: _Optional[str] = ..., task_id: _Optional[str] = ..., instruction: _Optional[str] = ..., harness_url: _Optional[str] = ...) -> None: ...

class EndTrialRequest(_message.Message):
    __slots__ = ("trial_id",)
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    def __init__(self, trial_id: _Optional[str] = ...) -> None: ...

class EndTrialResponse(_message.Message):
    __slots__ = ("trial_id", "state", "score_available", "score", "score_detail")
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    SCORE_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_DETAIL_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    state: TrialState
    score_available: bool
    score: float
    score_detail: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, trial_id: _Optional[str] = ..., state: _Optional[_Union[TrialState, str]] = ..., score_available: bool = ..., score: _Optional[float] = ..., score_detail: _Optional[_Iterable[str]] = ...) -> None: ...

class GetTrialRequest(_message.Message):
    __slots__ = ("trial_id", "cursor")
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    cursor: int
    def __init__(self, trial_id: _Optional[str] = ..., cursor: _Optional[int] = ...) -> None: ...

class GetTrialResponse(_message.Message):
    __slots__ = ("trial_id", "instruction", "benchmark_id", "task_id", "error", "score", "score_available", "score_detail", "state", "logs", "next_cursor", "run_id", "duration_sec", "api_calls", "api_errors", "event_count")
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    SCORE_DETAIL_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    LOGS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    DURATION_SEC_FIELD_NUMBER: _ClassVar[int]
    API_CALLS_FIELD_NUMBER: _ClassVar[int]
    API_ERRORS_FIELD_NUMBER: _ClassVar[int]
    EVENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    instruction: str
    benchmark_id: str
    task_id: str
    error: str
    score: float
    score_available: bool
    score_detail: _containers.RepeatedScalarFieldContainer[str]
    state: TrialState
    logs: _containers.RepeatedCompositeFieldContainer[LogLine]
    next_cursor: int
    run_id: str
    duration_sec: float
    api_calls: int
    api_errors: int
    event_count: int
    def __init__(self, trial_id: _Optional[str] = ..., instruction: _Optional[str] = ..., benchmark_id: _Optional[str] = ..., task_id: _Optional[str] = ..., error: _Optional[str] = ..., score: _Optional[float] = ..., score_available: bool = ..., score_detail: _Optional[_Iterable[str]] = ..., state: _Optional[_Union[TrialState, str]] = ..., logs: _Optional[_Iterable[_Union[LogLine, _Mapping]]] = ..., next_cursor: _Optional[int] = ..., run_id: _Optional[str] = ..., duration_sec: _Optional[float] = ..., api_calls: _Optional[int] = ..., api_errors: _Optional[int] = ..., event_count: _Optional[int] = ...) -> None: ...

class LogLine(_message.Message):
    __slots__ = ("time", "unix_ms", "text", "kind", "type", "data")
    TIME_FIELD_NUMBER: _ClassVar[int]
    UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    time: str
    unix_ms: int
    text: str
    kind: LogKind
    type: str
    data: _struct_pb2.Struct
    def __init__(self, time: _Optional[str] = ..., unix_ms: _Optional[int] = ..., text: _Optional[str] = ..., kind: _Optional[_Union[LogKind, str]] = ..., type: _Optional[str] = ..., data: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class StartRunRequest(_message.Message):
    __slots__ = ("benchmark_id", "name", "api_key")
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    API_KEY_FIELD_NUMBER: _ClassVar[int]
    benchmark_id: str
    name: str
    api_key: str
    def __init__(self, benchmark_id: _Optional[str] = ..., name: _Optional[str] = ..., api_key: _Optional[str] = ...) -> None: ...

class StartRunResponse(_message.Message):
    __slots__ = ("run_id", "benchmark_id", "trial_ids")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    TRIAL_IDS_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    benchmark_id: str
    trial_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, run_id: _Optional[str] = ..., benchmark_id: _Optional[str] = ..., trial_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class GetRunRequest(_message.Message):
    __slots__ = ("run_id",)
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    def __init__(self, run_id: _Optional[str] = ...) -> None: ...

class TrialStats(_message.Message):
    __slots__ = ("new_count", "running_count", "done_count", "error_count")
    NEW_COUNT_FIELD_NUMBER: _ClassVar[int]
    RUNNING_COUNT_FIELD_NUMBER: _ClassVar[int]
    DONE_COUNT_FIELD_NUMBER: _ClassVar[int]
    ERROR_COUNT_FIELD_NUMBER: _ClassVar[int]
    new_count: int
    running_count: int
    done_count: int
    error_count: int
    def __init__(self, new_count: _Optional[int] = ..., running_count: _Optional[int] = ..., done_count: _Optional[int] = ..., error_count: _Optional[int] = ...) -> None: ...

class TrialHead(_message.Message):
    __slots__ = ("trial_id", "task_id", "num", "state", "instruction", "score", "score_available", "error", "duration_sec", "api_calls", "api_errors", "event_count")
    TRIAL_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    NUM_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    DURATION_SEC_FIELD_NUMBER: _ClassVar[int]
    API_CALLS_FIELD_NUMBER: _ClassVar[int]
    API_ERRORS_FIELD_NUMBER: _ClassVar[int]
    EVENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    trial_id: str
    task_id: str
    num: int
    state: TrialState
    instruction: str
    score: float
    score_available: bool
    error: str
    duration_sec: float
    api_calls: int
    api_errors: int
    event_count: int
    def __init__(self, trial_id: _Optional[str] = ..., task_id: _Optional[str] = ..., num: _Optional[int] = ..., state: _Optional[_Union[TrialState, str]] = ..., instruction: _Optional[str] = ..., score: _Optional[float] = ..., score_available: bool = ..., error: _Optional[str] = ..., duration_sec: _Optional[float] = ..., api_calls: _Optional[int] = ..., api_errors: _Optional[int] = ..., event_count: _Optional[int] = ...) -> None: ...

class GetRunResponse(_message.Message):
    __slots__ = ("run_id", "benchmark_id", "name", "score", "score_available", "stats", "trials", "state", "policy")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    TRIALS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    benchmark_id: str
    name: str
    score: float
    score_available: bool
    stats: TrialStats
    trials: _containers.RepeatedCompositeFieldContainer[TrialHead]
    state: RunState
    policy: EvalPolicy
    def __init__(self, run_id: _Optional[str] = ..., benchmark_id: _Optional[str] = ..., name: _Optional[str] = ..., score: _Optional[float] = ..., score_available: bool = ..., stats: _Optional[_Union[TrialStats, _Mapping]] = ..., trials: _Optional[_Iterable[_Union[TrialHead, _Mapping]]] = ..., state: _Optional[_Union[RunState, str]] = ..., policy: _Optional[_Union[EvalPolicy, str]] = ...) -> None: ...

class SubmitRunRequest(_message.Message):
    __slots__ = ("run_id", "force")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    FORCE_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    force: bool
    def __init__(self, run_id: _Optional[str] = ..., force: bool = ...) -> None: ...

class SubmitRunResponse(_message.Message):
    __slots__ = ("run_id", "state")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    state: RunState
    def __init__(self, run_id: _Optional[str] = ..., state: _Optional[_Union[RunState, str]] = ...) -> None: ...

class StartPlaygroundRequest(_message.Message):
    __slots__ = ("benchmark_id", "task_id")
    BENCHMARK_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    benchmark_id: str
    task_id: str
    def __init__(self, benchmark_id: _Optional[str] = ..., task_id: _Optional[str] = ...) -> None: ...
