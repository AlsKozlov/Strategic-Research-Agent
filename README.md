# Strategic Research Agent

Strategic Research Agent — интеллектуальный AI-агент для выполнения аналитических исследований, анализа рынков и компаний, а также поддержки стратегических решений.

Агент является частью корпоративной AI-платформы, которая включает:

- Knowledge Bases
- Agentic RAG
- обработку документов
- анализ данных
- интеграции с корпоративными системами
- мультиагентную архитектуру

Strategic Research Agent использует эти возможности для выполнения сложных исследований и подготовки структурированных аналитических отчетов.

---

# Проблема

Сегодня сотрудники компаний тратят значительное время на:

- поиск информации
- анализ документов
- исследование рынков
- сравнение инструментов и поставщиков
- подготовку аналитических отчетов

Информация распределена между:

- внутренними документами компании
- корпоративными базами знаний
- интернет-источниками
- аналитическими отчетами
- таблицами и презентациями

Поиск и синтез этой информации требует значительных временных затрат.

---

# Решение

Strategic Research Agent автоматизирует процесс исследования и анализа.

Пользователь может задать вопрос или тему исследования, например:

- "Research AI infrastructure market"
- "Evaluate startup idea"
- "Analyze company Stripe"
- "Compare Snowflake vs Databricks"

Агент автоматически:

1. строит план исследования  
2. собирает информацию из разных источников  
3. анализирует данные  
4. генерирует структурированный аналитический отчет  

---

# Что делает PoC на демо

На демонстрации прототип должен показать:

- чат-интерфейс взаимодействия с агентом
- выполнение исследования по заданной теме
- использование RAG по внутренним документам
- поиск по web источникам
- генерацию structured research report

Отчет включает:

- executive summary
- ключевые выводы
- анализ источников
- сравнение альтернатив
- рекомендации

---

# Что НЕ делает PoC

В рамках PoC не реализуются:

- полноценные enterprise интеграции
- масштабируемая production инфраструктура
- интеграции с CRM/ERP
- сложная система авторизации
- автоматическая генерация презентаций

PoC фокусируется на демонстрации core AI возможностей:

- Agent orchestration
- RAG retrieval
- multi-source research
- structured report generation

---

# Основные возможности

Strategic Research Agent способен выполнять:

- research topics
- validate ideas
- analyze companies
- analyze markets
- compare vendors
- suggest strategy

---

# Использование Knowledge Base

Агент интегрирован с системой Knowledge Base платформы.

Пользователь может:

- загружать собственные документы
- создавать базы знаний
- использовать внутренние данные компании

Это позволяет агенту учитывать:

- внутренние документы
- корпоративный контекст
- исторические данные

и генерировать более точные аналитические выводы.

---

# Архитектурная идея

Strategic Research Agent является частью AI-платформы.

Платформа включает:

- Agent orchestration (LangGraph)
- RAG engine
- Vector database
- Knowledge bases
- document processing pipeline
- LLM inference

Агент использует эти компоненты для выполнения многошаговых исследований.

---

# Целевая аудитория

Система предназначена для:

- strategy teams
- consulting teams
- product managers
- executives
- analysts
- innovation teams

---

# Технологии

Основной стек:

- Python (реализация агента: `agent/strategic_research_agent/`, установка из корня: `pip install -e .`)
  - `config/` — настройки (`SRA_*`, ключи API)
  - `governance/` — политики безопасности (например, эвристики prompt injection)
  - `observability/` — логирование
  - `research/` — пайплайн исследования и A2A task store
  - `discovery/` — Agent Card для A2A
  - `interfaces/` — A2A (FastAPI), MCP, CLI
  - `workflow/` — LangGraph PAR (узлы в `workflow/nodes/`)
  - `tools/` — Tavily, arXiv, агрегаторы; `definitions.py` / `executor.py` — схемы и вызовы для агента с tool-calling (сам выбирает `web_search`, `arxiv_search`, `web_search_on_sites`)
  - `utils/` — HTTP, дедуп, retry
- LangGraph
- LLM models
- Vector database
- PostgreSQL
- S3 storage