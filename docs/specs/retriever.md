# Spec — Retriever

Контур получения внешней и внутренней информации для SRA.

## Источники (PoC)
| Источник | Тип | Реализация | Лимит |
|---|---|---|---|
| Tavily Search | web | [tools/tavily_search.py](../../strategic_research_agent/tools/tavily_search.py) | `max_web_results=5` |
| Tavily scoped | web по доменам | aggregator catalog ([tools/aggregators.py](../../strategic_research_agent/tools/aggregators.py)) | 5 |
| DuckDuckGo HTML | web fallback | tavily_search.py fallback | 5 |
| arXiv API | academic | [tools/arxiv.py](../../strategic_research_agent/tools/arxiv.py) | `max_arxiv_results=5` |
| Wikipedia REST | background | [tools/wikipedia.py](../../strategic_research_agent/tools/wikipedia.py) | `max_wikipedia_results=3` |
| content_fetch + trafilatura | full-page | [tools/content_fetch.py](../../strategic_research_agent/tools/content_fetch.py) | timeout 18s |
| `kb_context` (внешний) | внутр. документы | передаётся в metadata | произвольный текст |

## Индекс и хранилище
- У агента **нет собственного индекса** by design. Внешние API играют роль web-retrieval-сервиса.
- KB-индекс (vector store, chunking, embeddings) — **ответственность платформы**, не агента. Платформа делает top-k и передаёт результат в SRA через `metadata.kbContext` в A2A request body. Агент только потребляет.

## Поиск
- Запросы формируются в plan_node (LLM или heuristic) + расширяются в reflect_node при `needs_more`.
- В [subgraphs/web_deep.py](../../strategic_research_agent/workflow/subgraphs/web_deep.py): итеративный refine запроса до 3 раз; на каждой итерации до 5 URL.

## Reranking
- Для базового пути — встроенный score Tavily.
- Для deep_web: LLM-based relevance score `0.0–1.0`, порог принятия `deep_web_min_relevance=0.45`, ранний стоп при `deep_web_good_enough=0.72`.
- Отдельной cross-encoder модели нет.

## Дедупликация
- `dedupe_evidence()` ([utils/dedupe.py](../../strategic_research_agent/utils/dedupe.py)) — точное совпадение по `(url, title)`.
- Семантический dedup (embedding-cosine) — out of scope.

## Ограничения
- Latency на retrieval: целевой бюджет ≤ 35 с из 60 с end-to-end (см. [system-design.md](../system-design.md) §8).
- Cost: каждый Tavily-запрос платный, лимит — `tool_agent_max_iterations=10` × ≤2 запросов = ≤20 Tavily-вызовов на задачу.
- Reliability: при недоступности Tavily — DDG fallback; при недоступности OpenAI — heuristic_retrieval (см. [act.py](../../strategic_research_agent/workflow/nodes/act.py)).
- Privacy: запросы уходят к Tavily/OpenAI в чистом виде (gap — нет PII-маски).

## Интерфейс
Все retrieval-функции вызываются через `tools/executor.py`, который добавляет:
- `try/except` с outcome=`ok|error|empty|exception`;
- Prometheus histogram `sra_tool_latency_seconds{tool=...}`;
- truncation summary (`summarize_tool_result_for_llm`, ≤14k chars).
