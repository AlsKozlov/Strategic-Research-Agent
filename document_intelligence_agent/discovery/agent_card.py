from __future__ import annotations

from document_intelligence_agent.config import settings


def build_agent_card() -> dict:
    base = settings.base_url.rstrip("/")
    return {
        "name": "Document Intelligence Agent",
        "description": (
            "Multi-agent document processing: summarization, fact extraction, "
            "structured data extraction, document comparison, action item extraction, "
            "decision memo generation, format mapping, multi-document synthesis, "
            "conflict detection, and confidence attribution."
        ),
        "supportedInterfaces": [
            {
                "url": base,
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": "1.0",
            }
        ],
        "provider": {
            "url": "https://github.com/a2aproject/A2A",
            "organization": "Document Intelligence Agent (PoC)",
        },
        "version": "0.1.0",
        "documentationUrl": "https://github.com/a2aproject/A2A",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": True,
            "extensions": [
                {
                    "uri": "urn:dia:langgraph:dispatch",
                    "description": (
                        "classify → dispatch → [task node] → finalize, "
                        "implemented with LangGraph."
                    ),
                    "required": False,
                }
            ],
        },
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["application/json", "text/markdown"],
        "skills": [
            {
                "id": "summarize",
                "name": "Summarization",
                "description": "Condense one or more documents into a structured summary (executive, bullets, risks, actions).",
                "tags": ["summarize", "digest", "brief"],
                "examples": ["Summarize this contract", "Give me an executive summary of these reports"],
            },
            {
                "id": "fact_extract",
                "name": "Fact Extraction",
                "description": "Extract verifiable facts: numbers, dates, KPIs, obligations, and claims.",
                "tags": ["facts", "kpi", "extract"],
                "examples": ["Extract all facts and figures from this document"],
            },
            {
                "id": "structured_extract",
                "name": "Structured Data Extraction",
                "description": "Convert unstructured text to JSON or table following a schema.",
                "tags": ["json", "table", "schema", "extract"],
                "examples": ["Extract contract fields as JSON: parties, dates, penalties"],
            },
            {
                "id": "compare",
                "name": "Document Comparison",
                "description": "Diff two or more documents: added, removed, changed, contradicted.",
                "tags": ["compare", "diff", "versions"],
                "examples": ["Compare v1 and v2 of this contract and highlight changes"],
            },
            {
                "id": "action_items",
                "name": "Action Item Extraction",
                "description": "Identify tasks: who does what, by when, with dependencies.",
                "tags": ["tasks", "actions", "follow-up"],
                "examples": ["Extract all action items from this meeting transcript"],
            },
            {
                "id": "decision_memo",
                "name": "Decision Memo Generation",
                "description": "Produce a decision document: context, options, analysis, risks, recommendation.",
                "tags": ["decision", "memo", "recommendation"],
                "examples": ["Write a decision memo based on this analysis"],
            },
            {
                "id": "template_map",
                "name": "Template / Format Mapping",
                "description": "Transform content from one format to another (notes→PRD, transcript→report).",
                "tags": ["format", "convert", "template"],
                "examples": ["Convert these meeting notes into a PRD"],
            },
            {
                "id": "multi_synthesis",
                "name": "Multi-Document Synthesis",
                "description": "Combine multiple sources into a unified narrative without duplication.",
                "tags": ["synthesis", "combine", "merge"],
                "examples": ["Synthesize findings from these 5 research documents"],
            },
            {
                "id": "conflict_detect",
                "name": "Conflict Detection",
                "description": "Find contradictions across documents: conflicting numbers, claims, or conclusions.",
                "tags": ["conflicts", "contradictions", "inconsistencies"],
                "examples": ["Find any contradictions between these two reports"],
            },
            {
                "id": "confidence_attr",
                "name": "Confidence & Evidence Attribution",
                "description": "Annotate claims with source evidence and confidence levels (high/medium/low/unknown).",
                "tags": ["confidence", "evidence", "attribution"],
                "examples": ["Rate the reliability of each claim in this document"],
            },
        ],
    }
