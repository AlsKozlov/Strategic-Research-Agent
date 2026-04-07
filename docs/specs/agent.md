# Spec — Agent / Orchestrator

Спецификация LangGraph-оркестрации SRA (PAR-loop) и DIA (dispatch).

## SRA — Plan-Act-Reflect-Synthesize

### Узлы и переходы
| Узел | Вход | Выход | Переход |
|---|---|---|---|
| `plan_node` | query | task_type, plan_steps[], queries[] | → act |
| `act_node` | state | evidence[], tools_used[] | → reflect |
| `reflect_node` | state | needs_more (bool), notes, pending_queries[] | conditional |
| `synthesize_node` | evidence, task_type | report_markdown, confidence, caveats | → END |

### Правила переходов
```
plan → act → reflect → {
    needs_more && act_count < max_reflection_rounds (=2) → act
    else → synthesize
}
synthesize → END
recursion_limit = 25
```

### Stop conditions
- `act_count >= max_reflection_rounds` (жёсткий каp на reflective loop)
- `tool_agent_max_iterations >= 10` внутри act_node (cap на агентский цикл)
- `research_timeout_sec=90` (per-task wall time, проверяется на уровне engine — TODO жёсткий cancel, gap)
- `recursion_limit=25` LangGraph

### Retry / fallback
| Узел | Failure | Fallback |
|---|---|---|
| plan | LLM ошибка / нет ключа | `heuristic_plan()` (regex по ключевым словам) |
| act / tool_agent | LLM ошибка | `heuristic_retrieval()` — фиксированный набор Tavily+arXiv по queries |
| Tool вызов | exception | error-row, агент видит и может перевыбрать |
| reflect | JSON parse error | `needs_more=False` + caveat «reflect parse failed» |
| synthesize | пустой evidence | stub-report + `confidence=Low` + caveats |

## DIA — Classify-Dispatch

### Узлы
- `classify_node` → определяет один из 10 task_type
- `summarize / fact_extract / structured_extract / compare / action_items / decision_memo / template_map / multi_synthesis / conflict_detect`
- `finalize_node` (общий выход) — пакует confidence + evidence + gaps; для task_type=`confidence_attr` отрабатывает сам

### Правила переходов
```
classify → {one of 9 task nodes | confidence_attr → finalize directly}
each task_node → finalize → END
```

### Stop conditions
- `processing_timeout_sec=120`
- `max_documents=10`, `max_document_chars=80_000`
- `conflict_max_pairs=45` (C(10,2))

### Retry / fallback
- Каждый task-узел имеет heuristic-ветку при отсутствии OpenAI ключа.
- JSON-parse failure → graceful placeholder.

## Guardrails входа (общее)
1. `governance.safety.looks_suspicious(query)` — блокировка инъекций по regex.
2. `len(query) > 32_000` → reject.
3. (DIA) `document_has_injection(doc)` для каждого документа.
4. (gap) **Сейчас вызовы из A2A не подключены — нужно подключить в обёртке `engine.run_*` до запуска графа.**

## Guardrails выхода
- Synthesize system prompt требует citations `[title](url)`.
- Confidence обязательно проставляется (`High|Medium|Low`).
- Caveats[] — публичный канал «что не сошлось».
- (gap) **Citation validator** — пост-проверка, что все URL в отчёте присутствуют в `evidence[]`.

## Контракты API
- A2A request body см. [agent_card.json](../../strategic_research_agent/discovery/agent_card.py).
- Response: `task_id` → poll → `status: completed`, `artifact: { report, sources, confidence, caveats, latency }`.
