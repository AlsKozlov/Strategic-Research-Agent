# C4 — Component (SRA Research Engine)

Внутреннее устройство ядра Strategic Research Agent.

```mermaid
flowchart TB
    subgraph API["FastAPI A2A layer"]
        A2A[/POST /research-task/]
        TASK[/GET /task/{id}/]
        CARD[/GET /.well-known/agent.json/]
        METRICS[/GET /metrics/]
    end

    subgraph ENGINE["Research Engine"]
        ENG[engine.run_research]
        SAFE[governance.safety<br/>looks_suspicious]
        STORE[(TaskStore)]
    end

    subgraph GRAPH["LangGraph: Plan-Act-Reflect-Synthesize"]
        PLAN[plan_node<br/>LLM | heuristic_plan]
        ACT[act_node<br/>tool_agent loop ≤10]
        REFL[reflect_node<br/>LLM coverage check]
        SYN[synthesize_node<br/>templated report + citations]
    end

    subgraph TOOLS["Tool Layer"]
        EXEC[tools.executor]
        TAV[tavily_search]
        DDG[(DuckDuckGo fallback)]
        ARX[arxiv]
        WIK[wikipedia]
        FETCH[content_fetch + trafilatura]
        AGG[aggregators<br/>scoped domains]
        DEEP[subgraphs.web_deep<br/>prepare→search→enrich→score→decide→refine]
    end

    subgraph LLM["LLM client"]
        OAI[utils.openai_client]
    end

    subgraph OBS["Observability"]
        PROM[Prometheus metrics]
        LF[Langfuse CallbackHandler]
        LOG[JSON logging]
    end

    A2A --> ENG
    TASK --> STORE
    ENG --> SAFE
    SAFE -->|ok| PLAN
    SAFE -->|reject| A2A
    ENG --> STORE

    PLAN --> ACT
    ACT -->|tool_calls| EXEC
    EXEC --> TAV --> DDG
    EXEC --> ARX
    EXEC --> WIK
    EXEC --> AGG
    EXEC --> DEEP --> FETCH
    EXEC --> OAI
    ACT --> REFL
    REFL -->|needs_more & cnt<max| ACT
    REFL -->|done| SYN
    SYN --> ENG

    PLAN --> OAI
    REFL --> OAI
    SYN --> OAI
    DEEP --> OAI

    GRAPH -.metrics.-> PROM
    GRAPH -.traces.-> LF
    GRAPH -.logs.-> LOG
```
