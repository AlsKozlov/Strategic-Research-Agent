# Spec — Tools / API integrations

Контракты и поведение всех инструментов SRA.

Источник определений: [tools/definitions.py](../../strategic_research_agent/tools/definitions.py),
исполнение: [tools/executor.py](../../strategic_research_agent/tools/executor.py).

## Общий контракт
Каждый tool — асинхронная функция со схемой:
```python
async def tool(query: str, **kwargs) -> list[EvidenceRow]
EvidenceRow = {
    "kind": "web" | "academic" | "wiki" | "deep" | "error",
    "title": str,
    "url": str,
    "content": str,        # ≤ ~2000 chars
    "source": "tavily" | "ddg" | "arxiv" | "wikipedia" | "deep_web",
    "score": float | None  # для deep_web
}
```
Executor оборачивает вызов:
```
outcome = ok | error | empty | exception
metrics: sra_tool_invocations_total{tool, outcome}
         sra_tool_latency_seconds{tool}
```

## Tools

### 1. `web_search`
- API: Tavily Search (`/search`, `search_depth=advanced`)
- Вход: `query: str`, `max_results: int = 5`
- Выход: до 5 EvidenceRow `kind=web`
- Timeout: 30 с
- Retry: 3 × exp 0.6 ([utils/retry.py](../../strategic_research_agent/utils/retry.py))
- Fallback: DuckDuckGo HTML scraping
- Ошибки: 401/403 → return [], log `outcome=error`; 429 → retry; 5xx → retry → DDG
- Side effects: исходящие HTTPS, биллинг Tavily

### 2. `web_search_on_sites`
- Tavily + `include_domains=[...]`
- Вход: `query`, `domains: list[str]`
- Используется plan_node для scoped поиска (G2, Crunchbase, SEC, Statista, …)

### 3. `arxiv_search`
- API: arxiv.org `/api/query`
- Вход: `query`, `max_results: int = 5`
- Выход: EvidenceRow `kind=academic`
- Timeout: 20 с, retry × 3
- Особенности: парсинг XML, отсев пустых abstract'ов

### 4. `wikipedia_search`
- API: Wikipedia REST search + summary
- Timeout: 15 с, retry × 2

### 5. `deep_web_research` (subgraph)
- Поток: `prepare → tavily.advanced → content_fetch → score_relevance(LLM) → decide → refine → end`
- Параметры:
  - `deep_web_max_iterations=3`
  - `deep_web_urls_per_iteration=5`
  - `deep_web_fetch_timeout_sec=18`
  - `deep_web_min_relevance=0.45`
  - `deep_web_good_enough=0.72`
- Side effects: 5 параллельных GET'ов на итерацию; LLM-вызовы для оценки relevance.

### 6. OpenAI LLM (не tool, но внешний API)
- Модель по умолчанию: `gpt-4o-mini`
- Используется в plan / tool_agent / reflect / synthesize / deep_web score
- Timeout: 60 с/вызов; retry: 2 (через клиент)
- Cost cap: только через лимиты iterations (нет $-budget guard, gap)

## Обработка ошибок (унифицированно)
- Любая exception → executor вернёт `[{"kind":"error", "title":..., "content":str(e), "source":...}]`, метрика `outcome=exception`.
- Empty (`[]`) → metric `outcome=empty`.
- Tool-агент видит error rows и может выбрать другой источник.

## Защита
- Whitelist: tool-агент знает только функции из `definitions.py`. Динамической регистрации нет.
- LLM tool_calls парсятся и валидируются на имя/JSON-аргументы перед вызовом ([tool_runner.py](../../strategic_research_agent/workflow/nodes/tool_runner.py)).
- Запросы к внешним API не содержат секретов; ключи берутся только из env.
- TODO: rate-limit на уровень executor (gap).
