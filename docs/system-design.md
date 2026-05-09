# System Design — Strategic Research Agent (PoC)

Статус: зафиксировано перед разработкой PoC, агентский трек.
Дата: 2026-04-06 (синхронизировано с обновлённым [README.md](../README.md)).

> **Scope.** Оба агента — это **компоненты корпоративной AI-платформы**, подключаемые через A2A. Платформа (вне scope этого репозитория) отвечает за: чат-UI, upload документов, persistent Knowledge Base, vector store, объектное хранилище, авторизацию. Агенты получают уже подготовленный контекст: SRA — через `metadata.kbContext` (top-k chunks из KB платформы), DIA — через `documents[]` в request body. Соответственно требования «чат-UI / upload / pgvector / S3» из README **не относятся к этим агентам** и в gap-листе не учитываются.
Связанные документы: [product-proposal.md](product-proposal.md), [governance.md](governance.md), [code-review.md](code-review.md), [diagrams/](diagrams/), [specs/](specs/).

> Проект находится на **агентском треке**. Приоритеты дизайна: качество ответа агента, контроль галлюцинаций, защита от prompt injection, fallback-цепочки на каждом шаге LLM-пайплайна. Инфраструктурные требования (HA, autoscale, GPU pool) находятся за рамками PoC.

---

## 1. Ключевые архитектурные решения

| # | Решение | Обоснование |
|---|---|---|
| 1 | **LangGraph как orchestrator** обоих агентов | Явные узлы и conditional edges → проще верифицировать поведение и навешивать observability на каждом шаге. |
| 2 | **Два независимых агента (SRA + DIA)** через A2A protocol | Разделение зон ответственности: SRA — внешние источники + синтез, DIA — обработка корпоративных документов. SRA может вызывать DIA через A2A. |
| 3 | **Plan-Act-Reflect-Synthesize (PAR)** для SRA | Управляемый цикл с явной точкой решения «нужно ли ещё искать», ограниченный `max_reflection_rounds`. |
| 4 | **Tool-calling агент внутри Act**, не fixed pipeline | Позволяет LLM выбирать источник под задачу, но ограничен `tool_agent_max_iterations=10`, чтобы не разойтись. |
| 5 | **Heuristic fallback на каждом LLM-узле** | Система должна деградировать, а не падать при отсутствии ключа OpenAI или ошибке LLM. |
| 6 | **Evidence-first synthesis**: LLM получает только дайджест собранных evidence | Снижает галлюцинации; цитаты обязаны ссылаться на собранные URL. |
| 7 | **Stateful TaskStore + async background execution** | A2A-интерфейс асинхронный: запрос ставится в очередь, статус опрашивается. PoC использует in-memory store. |
| 8 | **Observability через Prometheus + Langfuse** с самого начала | Без трейсов агента невозможно отлаживать качество. |
| 9 | **Guardrails как отдельный модуль `governance/safety.py`** перед входом в граф | Все проверки (injection, длина, документы) применяются до запуска LangGraph. |
| 10 | **Confidence + caveats как обязательная часть ответа** | Пользователь всегда видит уровень доверия и недостающие данные. |

---

## 2. Модули и их роли

### Strategic Research Agent
| Модуль | Файл | Роль |
|---|---|---|
| Engine | [research/engine.py](../strategic_research_agent/research/engine.py) | Точка входа, валидация запроса, запуск графа, упаковка результата |
| Workflow / Graph | [workflow/graph.py](../strategic_research_agent/workflow/graph.py) | Сборка LangGraph, conditional edges, тайминги узлов |
| Plan node | [workflow/nodes/plan.py](../strategic_research_agent/workflow/nodes/plan.py) | Классификация задачи + выбор источников (LLM/heuristic) |
| Act node | [workflow/nodes/act.py](../strategic_research_agent/workflow/nodes/act.py) | Запуск tool-agent или эвристического retrieval |
| Tool runner | [workflow/nodes/tool_runner.py](../strategic_research_agent/workflow/nodes/tool_runner.py) | Агентский цикл tool-calls с OpenAI |
| Reflect node | [workflow/nodes/reflect.py](../strategic_research_agent/workflow/nodes/reflect.py) | Решение «достаточно ли evidence», правки plan |
| Synthesize node | [workflow/nodes/synthesize.py](../strategic_research_agent/workflow/nodes/synthesize.py) | Шаблонированный отчёт + citations + confidence |
| Deep web subgraph | [workflow/subgraphs/web_deep.py](../strategic_research_agent/workflow/subgraphs/web_deep.py) | Tavily advanced + extraction + relevance + refine |
| Tools | [tools/](../strategic_research_agent/tools/) | Tavily, arXiv, Wikipedia, content_fetch, scoped aggregators, executor |
| Governance | [governance/safety.py](../strategic_research_agent/governance/safety.py) | Регекс-фильтр инъекций, ограничения на запрос |
| Observability | [observability/](../strategic_research_agent/observability/) | Prometheus metrics, Langfuse client, JSON-логи |
| Interfaces | [interfaces/](../strategic_research_agent/interfaces/) | A2A FastAPI, CLI, MCP-шим |
| Discovery | [discovery/agent_card.py](../strategic_research_agent/discovery/agent_card.py) | `/.well-known/agent.json` |
| Config | [config/settings.py](../strategic_research_agent/config/settings.py) | pydantic-settings, env `SRA_*` |

### Document Intelligence Agent
| Модуль | Файл | Роль |
|---|---|---|
| Engine | [processing/engine.py](../document_intelligence_agent/processing/engine.py) | Валидация документов, запуск графа |
| Workflow / Graph | [workflow/graph.py](../document_intelligence_agent/workflow/graph.py) | Star-dispatch: classify → task → finalize |
| Classify | [workflow/nodes/classify.py](../document_intelligence_agent/workflow/nodes/classify.py) | Определение task_type |
| Task nodes | [workflow/nodes/](../document_intelligence_agent/workflow/nodes/) | summarize, fact_extract, structured_extract, compare, action_items, decision_memo, template_map, multi_synthesis, conflict_detect |
| Finalize | [workflow/nodes/finalize.py](../document_intelligence_agent/workflow/nodes/finalize.py) | Сборка confidence + evidence + gaps, ветка confidence_attr |
| Governance | [governance/safety.py](../document_intelligence_agent/governance/safety.py) | Фильтр инъекций в запросе и в документах |
| Остальное | … | Симметрично SRA |

---

## 3. Основной workflow выполнения задачи (SRA)

```
A2A POST /research-task
   │
   ▼
[engine.run_research]
   │  ├─ safety.looks_suspicious()  ── reject ──► A2A 400
   │  └─ build initial ResearchState
   ▼
[plan_node]   LLM (or heuristic) → task_type, plan_steps, queries
   ▼
[act_node]    tool_agent loop (≤ 10 iters):
   │           web_search / arxiv_search / web_search_on_sites /
   │           deep_web_research / wikipedia_search
   │          → evidence[] (deduped)
   ▼
[reflect_node] LLM coverage check
   │   needs_more && act_count < max_reflection_rounds
   │           ├── true ──► back to act_node
   │           └── false ─► synthesize
   ▼
[synthesize_node] LLM → markdown report + confidence + caveats
   ▼
TaskStore.update(result)  →  A2A GET /task/{id}
```

DIA workflow проще — `classify → один из 9 task-узлов → finalize`. Задача определяется один раз и не пересматривается.

См. подробные диаграммы в [diagrams/workflow-sra.md](diagrams/workflow-sra.md) и [diagrams/workflow-dia.md](diagrams/workflow-dia.md).

---

## 4. State, memory, context handling

**Состояние графа** — единственный канал коммуникации между узлами.

| Уровень | SRA | DIA |
|---|---|---|
| Per-request state | `ResearchState` (TypedDict) | `DocIntelState` (TypedDict) |
| Persistence запроса | `TaskStore` (in-memory map task_id → result) | `TaskStore` |
| Cross-request memory | **Нет** | **Нет** |
| Внешний контекст | `kb_context` (готовый текст, передаётся через metadata.kbContext) | `documents[]` + `doc_meta[]` |
| Trace context | `trace_id`, `session_id`, `user_id` (только для Langfuse) | то же |

**Context budget** (PoC):
- SRA: системный промпт ~1.5k токенов, evidence digest обрезается до 14k символов в [tools/executor.py](../strategic_research_agent/tools/executor.py), синтез — `max_tokens=6000`.
- DIA: `max_document_chars=80_000` на документ, `max_documents=10`, multi_synthesis включает map-reduce при ≥3 документах.

**Memory policy для PoC:** stateless по запросу. Долговременная память (vector store, диалоги) выходит за рамки PoC и описана как будущее расширение в [specs/memory.md](specs/memory.md).

---

## 5. Retrieval-контур

```
plan_node (task_type, queries)
   │
   ▼
act_node ── tool_agent ──► OpenAI tool-calls ──► tools/executor
                                                    │
              ┌────────────┬────────────┬───────────┼───────────┬──────────────┐
              ▼            ▼            ▼           ▼           ▼              ▼
        Tavily web   Tavily scoped  arXiv API   Wikipedia  content_fetch  deep_web subgraph
        (+ DDG       (G2/SEC/…)                            (trafilatura)   (Tavily adv +
         fallback)                                                          extract +
                                                                            LLM relevance +
                                                                            refine ≤ 3)
              └────────────┴────────────┴───────────┴───────────┴──────────────┘
                                       │
                                       ▼
                          dedupe_evidence (по url+title)
                                       │
                                       ▼
                              evidence[] в state
```

Особенности:
- **Reranking**: для PoC — встроенный score Tavily + LLM-relevance в deep_web subgraph (порог `0.45`, «достаточно хорошо» `0.72`). Отдельной модели-реранкера нет.
- **Дедупликация**: точное совпадение по `(url, title)`. Семантический dedupe — out of scope.
- **KB retrieval**: для PoC — внешний `kb_context` подаётся через metadata. Полноценный retriever (vector index) описан в [specs/retriever.md](specs/retriever.md) как next step.
- **DIA** не имеет retrieval-контура: документы передаются клиентом и обрабатываются in-memory.

Подробности в [specs/retriever.md](specs/retriever.md).

---

## 6. Tool / API интеграции

| Tool | Внешний API | Контракт | Timeout | Retry | Side effects |
|---|---|---|---|---|---|
| `web_search` | Tavily Search | `query, max_results` | 30s | 3 × exp 0.6 | — |
| `web_search` (fallback) | DuckDuckGo HTML | то же | 15s | 1 | — |
| `web_search_on_sites` | Tavily + include_domains | `query, domains[]` | 30s | 3 | — |
| `arxiv_search` | arxiv.org export API | `query, max_results` | 20s | 3 | — |
| `wikipedia_search` | Wikipedia REST | `query` | 15s | 2 | — |
| `deep_web_research` | Tavily + trafilatura fetch | `query` | 18s/URL | 3 | сетевые fetches |
| OpenAI LLM | OpenAI Chat Completions | tool-calls / JSON | 60s/call | 2 | биллинг |

Полные контракты, обработка ошибок и схемы ответов — в [specs/tools.md](specs/tools.md).

---

## 7. Failure modes, fallbacks, guardrails

### Failure modes
| Где | Что может сломаться | Что делает система |
|---|---|---|
| `safety.looks_suspicious` | Promt injection / превышение длины | Запрос отклоняется до запуска графа (см. gap §10) |
| `plan_node` LLM | Нет ключа / 5xx / parse error | `heuristic_plan()` по ключевым словам |
| `act_node` tool_agent | LLM-loop не останавливается | Hard cap `tool_agent_max_iterations=10` |
| Tavily | 429 / 5xx / timeout | Retry × 3 → DuckDuckGo fallback |
| arXiv | Сеть / парсинг | Retry × 3 → пустой результат, evidence-row с `kind=error` |
| `deep_web` fetch | Невалидный HTML, anti-bot | trafilatura возвращает пусто, score=0, отбрасывается |
| `reflect_node` | LLM JSON parse fail | `needs_more=False`, в caveats отметка |
| `synthesize_node` | Пустые evidence | Заглушечный отчёт + `confidence=Low` + caveats |
| Recursion / loop | Зацикливание графа | `recursion_limit=25` + `max_reflection_rounds=2` |
| Total task | Превышение времени | `research_timeout_sec=90` (TODO: жёсткий cancel, см. §10) |

### Guardrails
- **Input filter**: regex на «ignore previous», «system:», jailbreak-паттерны (governance/safety.py).
- **Citations enforcement**: system prompt synthesize требует `[title](url)` для каждого факта.
- **Confidence transparency**: `High/Medium/Low` всегда в ответе.
- **Caveats**: пустые источники, отсутствующий ключ, устаревшие данные → caveats[].
- **Tool sandbox**: список инструментов фиксирован в [tools/definitions.py](../strategic_research_agent/tools/definitions.py); LLM не может вызвать что-то за его пределами.
- **DIA injection check** проверяется не только в request, но и в теле документов.

### Что планируется добавить (gap → план)
1. Подключить `safety.looks_suspicious()` к A2A endpoint'ам (см. [specs/agent.md](specs/agent.md)).
2. Citation validator на пост-этапе synthesize (URL должны быть из evidence).
3. PII-маскинг перед уходом данных в Tavily/OpenAI.
4. Latency budget per node + жёсткий cancel при превышении.

---

## 8. Технические и операционные ограничения

| Категория | Ограничение | Источник |
|---|---|---|
| Latency (SRA, PoC цель) | ≤ 60 с end-to-end | proposal |
| Latency (текущий cap) | `research_timeout_sec=90` | settings |
| Latency (DIA) | `processing_timeout_sec=120` | settings |
| Кол-во web результатов | 5/запрос (`max_web_results`) | settings |
| Кол-во arXiv | 5/запрос | settings |
| Reflection iterations | ≤ 2 | settings |
| Tool agent iterations | ≤ 10 | settings |
| Deep web iterations | ≤ 3, ≤ 5 URL/iter | settings |
| Документов в DIA | ≤ 10, ≤ 80 000 chars каждый | settings |
| Конкурентность | 1 запрос на agent (PoC, single-process) | архитектура |
| Cost cap | вручную через выбор `gpt-4o-mini`; жёсткого budget guard нет | gap |
| Reliability | best-effort, без HA, in-memory TaskStore | PoC |
| Secrets | `.env` + pydantic-settings, никаких vault'ов в PoC | config |
| Модели | `openai_model=gpt-4o-mini` (default) | settings, [specs/serving.md](specs/serving.md) |

---

## 9. Что уже есть и что делаем дальше

**Готово (см. [code-review.md](code-review.md)):**
- LangGraph-граф SRA и DIA, узлы, conditional edges.
- Tool-набор, executor, deep_web subgraph.
- A2A FastAPI, Agent Card, CLI, MCP-шим.
- Prometheus + Langfuse observability.
- Heuristic fallbacks.

**Закрыть до выхода в PoC-демо:**
1. Wire-up safety.looks_suspicious в A2A.
2. Latency budget per node + soft-degradation.
3. Citation validator post-synthesize.
4. KB retriever (или явно вынести из scope).
5. SRA → DIA вызов через A2A для «внутренних документов».
6. Confidence калибровка с учётом противоречий и авторитетности.

---

## 10. Точки контроля (review checkpoints)

- **CP-1 Architecture freeze (этот документ).** Согласован состав модулей, контракты, ограничения.
- **CP-2 Quality baseline.** Набор golden queries (10–20), ручная разметка ожидаемых отчётов, baseline по precision цитат и confidence calibration.
- **CP-3 Guardrails review.** Включены injection-фильтр, citation validator, PII-маска. Прогон adversarial-набора.
- **CP-4 Latency review.** Все стадии укладываются в бюджет 60с на 90% golden queries.
- **CP-5 Demo readiness.** End-to-end happy path + 3 edge cases (пустые источники, инъекция, противоречивые документы).

Метрики и evals — в [specs/observability.md](specs/observability.md).
