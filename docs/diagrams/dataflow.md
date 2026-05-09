# Data Flow — что хранится, что логируется, что уходит наружу

Показывает движение данных через систему: что является входом, что persist-ится в TaskStore, что отправляется во внешние сервисы, что попадает в observability.

```mermaid
flowchart LR
    subgraph CLIENT["Client"]
        Q[query / kb_context / metadata<br/>session_id, user_id]
    end

    subgraph SRA["SRA process"]
        VAL[safety filter]
        ST[(TaskStore<br/>in-memory<br/>task_id → status, result)]
        STATE[ResearchState<br/>query, plan, evidence,<br/>reflection_notes,<br/>confidence, caveats]
        SYN[synthesize → Markdown report]
    end

    subgraph EXT["External services"]
        TVL[Tavily / DDG]
        ARX[arXiv]
        WIK[Wikipedia]
        OAI[OpenAI]
    end

    subgraph OBS["Observability"]
        LF[Langfuse traces<br/>query[:512], plan, tools, tokens]
        PR[Prometheus metrics<br/>task latency, node duration,<br/>tool outcomes, LLM tokens]
        LG[JSON logs<br/>task_id, errors]
    end

    Q --> VAL
    VAL -- reject --> CLIENT
    VAL -- ok --> STATE
    STATE -- task_id --> ST
    STATE -- queries --> TVL
    STATE -- queries --> ARX
    STATE -- queries --> WIK
    STATE -- prompts (query + evidence digest) --> OAI

    TVL -- snippets, urls --> STATE
    ARX -- titles, abstracts --> STATE
    WIK -- summaries --> STATE
    OAI -- plan / tool-calls / report --> STATE

    STATE --> SYN
    SYN -- report + confidence + caveats --> ST
    ST -- on GET /task/{id} --> CLIENT

    STATE -.tracing.-> LF
    STATE -.metrics.-> PR
    STATE -.logs.-> LG

    classDef warn fill:#fee,stroke:#c33,stroke-width:1px;
    class TVL,OAI warn;
```

**Что persist-ится (PoC):**
- TaskStore: task_id, status, ResearchResult (markdown, sources, confidence, caveats, latency).
- Langfuse: трейс с обрезанным query (≤512 символов), tags, tool-calls, tokens.
- Prometheus: только метрики (без PII).

**Что НЕ хранится (PoC):**
- raw HTML страниц после extract;
- историю диалогов / сессии;
- evidence между запросами.

**Что уходит во внешние сервисы:**
- В Tavily/DuckDuckGo: текст поисковых запросов (`query` или его перефразировки).
- В OpenAI: системный промпт, запрос пользователя, evidence digest (≤14k символов).
- В Langfuse: метаданные трейса, имена tools, размеры payload (контент ограничивается).

**Точки риска утечки PII** (см. governance.md):
- Любой текст в `query` уходит в Tavily и OpenAI как есть. Маскинг — gap, см. [specs/agent.md](../specs/agent.md).
- Документы DIA (`documents[]`) уходят в OpenAI целиком (до 80k chars × 10).
