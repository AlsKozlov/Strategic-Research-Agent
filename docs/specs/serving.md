# Spec — Serving / Config

## Запуск

### SRA
```
uvicorn strategic_research_agent.interfaces.a2a:app --host 0.0.0.0 --port 8080
```
Endpoint'ы:
- `POST /research-task` — постановка задачи
- `GET /task/{task_id}` — статус/результат
- `GET /.well-known/agent.json` — Agent Card (discovery)
- `GET /metrics` — Prometheus
- `GET /healthz` (если есть) — liveness

### DIA
```
uvicorn document_intelligence_agent.interfaces.a2a:app --host 0.0.0.0 --port 8081
```

### CLI (для отладки)
```
python -m strategic_research_agent.interfaces.cli "Compare Snowflake vs Databricks"
```

## Конфигурация
Pydantic Settings, env-prefix `SRA_` / `DIA_`.

### Ключевые переменные SRA ([config/settings.py](../../strategic_research_agent/config/settings.py))
| Переменная | Default | Описание |
|---|---|---|
| `SRA_OPENAI_API_KEY` / `OPENAI_API_KEY` | — | Ключ OpenAI |
| `SRA_OPENAI_MODEL` | `gpt-4o-mini` | Модель LLM |
| `SRA_TAVILY_API_KEY` | — | Ключ Tavily |
| `SRA_MAX_WEB_RESULTS` | 5 | |
| `SRA_MAX_ARXIV_RESULTS` | 5 | |
| `SRA_MAX_REFLECTION_ROUNDS` | 2 | |
| `SRA_TOOL_AGENT_MAX_ITERATIONS` | 10 | |
| `SRA_RESEARCH_TIMEOUT_SEC` | 90 | |
| `SRA_DEEP_WEB_MAX_ITERATIONS` | 3 | |
| `SRA_DEEP_WEB_FETCH_TIMEOUT_SEC` | 18 | |
| `SRA_LANGFUSE_ENABLED` | false | |
| `SRA_LANGFUSE_HOST` / `_PUBLIC_KEY` / `_SECRET_KEY` | — | |
| `SRA_HOST` / `SRA_PORT` | `0.0.0.0` / `8080` | |

### Ключевые переменные DIA
| Переменная | Default |
|---|---|
| `DIA_OPENAI_MODEL` | `gpt-4o-mini` |
| `DIA_PROCESSING_TIMEOUT_SEC` | 120 |
| `DIA_MAX_DOCUMENT_CHARS` | 80 000 |
| `DIA_MAX_DOCUMENTS` | 10 |
| `DIA_MULTI_SYNTHESIS_MAP_THRESHOLD` | 3 |
| `DIA_CONFLICT_MAX_PAIRS` | 45 |
| `DIA_PORT` | 8081 |

## Секреты
- Только через env / `.env` файл (pydantic-settings).
- Никаких vault'ов в PoC; для production — HashiCorp Vault / AWS Secrets Manager.
- Ключи **не логируются** (pydantic SecretStr), но проверки покрытия нет — gap.

## Версии моделей
- `gpt-4o-mini` зафиксирован в settings; апгрейд через env.
- Подмена модели не требует кода.
- TODO: записать актуальную версию модели в каждый Langfuse trace (gap).

## Reliability (PoC)
- Single process, без HA.
- TaskStore in-memory → перезапуск процесса = потеря активных задач.
- Healthcheck → планируется `/healthz` с проверкой OpenAI/Tavily ping.
- Graceful shutdown: Langfuse `flush()` в lifespan ([interfaces/a2a.py](../../strategic_research_agent/interfaces/a2a.py)).
