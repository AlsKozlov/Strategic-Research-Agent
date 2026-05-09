# Spec — Observability / Evals

## Логи
- Формат: JSON через [observability/logging.py](../../strategic_research_agent/observability/logging.py).
- Уровень: `SRA_LOG_LEVEL` (default INFO).
- Поля: `timestamp, level, logger, message, task_id?, error?`.
- Что НЕ логируется: полное содержимое evidence (только размеры), API-ключи.

## Метрики (Prometheus)

### SRA ([observability/metrics.py](../../strategic_research_agent/observability/metrics.py))
| Метрика | Тип | Лейблы | Назначение |
|---|---|---|---|
| `sra_research_tasks_total` | Counter | `status` | success/failure rate |
| `sra_research_task_latency_seconds` | Histogram | — | end-to-end latency, buckets 0.5–300 |
| `sra_node_duration_seconds` | Histogram | `node` | per-node timing (plan/act/reflect/synth) |
| `sra_llm_calls_total` | Counter | `model, node` | стоимость по узлам |
| `sra_llm_tokens_total` | Counter | `model, node, kind` (prompt/completion) | бюджет токенов |
| `sra_llm_call_latency_seconds` | Histogram | `model, node` | latency LLM |
| `sra_tool_invocations_total` | Counter | `tool, outcome` | здоровье tool-уровня |
| `sra_tool_latency_seconds` | Histogram | `tool` | latency external API |

### DIA
- `document_jobs_total{status}`
- `document_job_latency_seconds`
- `documents_processed_total`
- (плюс LLM/tool метрики аналогично)

Endpoint: `/metrics` через Prometheus FastAPI Instrumentator.

## Трейсы (Langfuse)
- Singleton клиент, lazy init ([observability/langfuse_client.py](../../strategic_research_agent/observability/langfuse_client.py)).
- LangChain CallbackHandler подключается в graph.invoke config → автоматический trace узлов и LLM-вызовов.
- Метаданные трейса: `query[:512], kb_chunks, trace_id, tags=["strategic-research-agent","langgraph"]`.
- `langfuse_sample_rate` (default 1.0) — для прода понизить.
- Flush в lifespan FastAPI.

## Что трейсится
- Полный путь графа (узлы, переходы)
- Tool-calls с агрументами и outcome
- LLM запросы / ответы (с обрезкой по объёму)
- Ошибки и stack traces
- Latency на каждом шаге

## Evals (план PoC)

### Golden set
- 20 запросов (по 5 на каждый scenario из proposal: research / company / compare / idea validation).
- Эталонные отчёты с разметкой ключевых фактов и обязательных источников.

### Метрики качества
| Метрика | Способ измерения | Цель PoC |
|---|---|---|
| Citation precision | доля цитат, чьи URL действительно есть в evidence | ≥ 0.95 |
| Citation coverage | доля ключевых фактов с цитатой | ≥ 0.8 |
| Confidence calibration | корреляция confidence vs human rating | спирмен > 0.5 |
| End-to-end latency p90 | research_task_latency_seconds | ≤ 60 с |
| Tool error rate | tool_invocations_total{outcome=error\|exception} / total | ≤ 5% |
| Adversarial guard rate | % инъекций, отклонённых до графа | 100% (после wire-up) |

### Прогон
- CI-job: nightly на golden set, экспорт в Langfuse → ручная проверка регрессий.
- Adversarial set отдельно: 20 jailbreak-промптов + 5 документов с инъекциями.

## Алерты (план)
- `sra_research_task_latency_seconds_p95 > 90s` — degradation
- `sra_tool_invocations_total{outcome="exception"} rate > 0.1` — внешние API
- `sra_research_tasks_total{status="failure"} rate > 0.05`
- LLM 5xx burst — circuit breaker (TODO).
