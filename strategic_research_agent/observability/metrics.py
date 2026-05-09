"""Prometheus metrics for Strategic Research Agent.

All metrics are defined as module-level singletons so the same instances are
reused across requests. Exposed via the `/metrics` endpoint configured in
`interfaces/a2a.py` (prometheus_fastapi_instrumentator).
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

_LABELS_TASK = ("status",)
_LABELS_NODE = ("node",)
_LABELS_LLM = ("model", "node")
_LABELS_TOOL = ("tool", "outcome")

# Task lifecycle
research_tasks_total = Counter(
    "sra_research_tasks_total",
    "Total research tasks processed by the strategic research agent.",
    _LABELS_TASK,
)

research_task_latency_seconds = Histogram(
    "sra_research_task_latency_seconds",
    "End-to-end latency of a research task (plan → synthesize).",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 90, 120, 180, 300),
)

# Per-node timings
node_duration_seconds = Histogram(
    "sra_node_duration_seconds",
    "Duration of a single LangGraph node execution.",
    _LABELS_NODE,
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

# LLM call accounting
llm_calls_total = Counter(
    "sra_llm_calls_total",
    "Number of LLM calls issued by the agent.",
    _LABELS_LLM,
)

llm_tokens_total = Counter(
    "sra_llm_tokens_total",
    "Total LLM tokens consumed (prompt + completion).",
    ("model", "node", "kind"),  # kind ∈ {prompt, completion}
)

llm_call_latency_seconds = Histogram(
    "sra_llm_call_latency_seconds",
    "Latency of a single LLM call.",
    _LABELS_LLM,
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

# Tool usage (web search, arxiv, fetch, …)
tool_invocations_total = Counter(
    "sra_tool_invocations_total",
    "Number of tool invocations grouped by outcome.",
    _LABELS_TOOL,
)

tool_latency_seconds = Histogram(
    "sra_tool_latency_seconds",
    "Latency of a tool invocation.",
    ("tool",),
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)


__all__ = [
    "research_tasks_total",
    "research_task_latency_seconds",
    "node_duration_seconds",
    "llm_calls_total",
    "llm_tokens_total",
    "llm_call_latency_seconds",
    "tool_invocations_total",
    "tool_latency_seconds",
]
