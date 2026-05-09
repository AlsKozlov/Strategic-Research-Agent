"""Prometheus metrics for Document Intelligence Agent."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

document_jobs_total = Counter(
    "dia_document_jobs_total",
    "Total document intelligence jobs processed.",
    ("status",),
)

document_job_latency_seconds = Histogram(
    "dia_document_job_latency_seconds",
    "End-to-end latency of a document intelligence job.",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120, 180, 300, 600),
)

node_duration_seconds = Histogram(
    "dia_node_duration_seconds",
    "Duration of a single LangGraph node execution.",
    ("node",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

llm_calls_total = Counter(
    "dia_llm_calls_total",
    "Number of LLM calls issued by the agent.",
    ("model", "node"),
)

documents_processed_total = Counter(
    "dia_documents_processed_total",
    "Number of individual documents processed.",
)


__all__ = [
    "document_jobs_total",
    "document_job_latency_seconds",
    "node_duration_seconds",
    "llm_calls_total",
    "documents_processed_total",
]
