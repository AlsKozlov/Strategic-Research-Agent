# Spec — Memory / Context

## Уровни состояния

| Уровень | SRA | DIA | Persistence |
|---|---|---|---|
| Per-node state | `ResearchState` (TypedDict) | `DocIntelState` | в памяти LangGraph |
| Per-task state | `ResearchResult` | `DocIntelResult` | TaskStore (in-memory dict) |
| Session memory | — | — | **отсутствует** в PoC |
| Long-term KB | внешний `kb_context` | сами `documents[]` | вне процесса |

## Session policy
PoC полностью **stateless по сессии**. Каждый запрос — изолированная задача. `session_id` и `user_id` принимаются только для трейсинга в Langfuse, но никак не влияют на исполнение.

Обоснование: на этапе PoC нам важнее воспроизводимость каждого ответа, а не накопление контекста.

## Context budget

| Стадия | Лимит |
|---|---|
| System prompt synthesize | ≈1.5k токенов |
| Evidence digest для LLM | ≤ 14 000 символов (truncate в [tools/executor.py](../../strategic_research_agent/tools/executor.py)) |
| Synthesize output | `max_tokens=6000`, `temperature=0.25` |
| Document body (DIA) | `max_document_chars=80_000` |
| Documents per request (DIA) | `max_documents=10` |
| Map-reduce trigger (DIA multi_synth) | `≥ 3 documents` |

## TaskStore (PoC)
- in-memory `dict[task_id -> TaskRecord]` ([research/task_store.py](../../strategic_research_agent/research/task_store.py))
- TaskRecord: `status (pending|running|completed|failed)`, `result`, `error`, `created_at`, `updated_at`
- TTL не реализован — gap; для PoC не критично, на проде потребуется persistence (Redis/Postgres) и cleanup.

## Что НЕ хранится
- Тексты документов после finalize (DIA).
- Полные HTML страниц после deep_web extraction.
- Промежуточные LLM-ответы (только в Langfuse traces).
- Истории взаимодействий между запросами.

## Будущее (вне PoC)
- Добавить **Conversation memory** (последние N запросов пользователя) для уточняющих диалогов.
- Добавить **Knowledge memory** (vector store) для кэширования research-результатов с TTL по теме.
- Persistent TaskStore.
