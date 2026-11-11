"""
LangGraph Agent Workflow State Definition for NotebookLM Lite.
Maintains state across question understanding, routing, MCP tool execution,
evidence collection, citation verification, and answer generation.
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    # Core session & identification
    question: str
    original_query: str
    notebook_id: str
    user_id: str
    document_ids: Optional[List[str]]
    conversation_id: Optional[str]

    # Intent analysis & routing
    intent: str  # SIMPLE_QUESTION, MULTI_DOCUMENT_QUESTION, COMPARISON_QUESTION, DOCUMENT_SUMMARY, PAGE_SPECIFIC_QUESTION, INSUFFICIENT_EVIDENCE
    intent_reasoning: str
    target_page: Optional[int]
    target_document_id: Optional[str]
    sub_questions: List[str]
    selected_tools: List[str]

    # MCP tool calling & execution
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    retrieved_documents: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]

    # Evidence & grounded generation
    evidence: Dict[str, Any]
    context_text: str
    generated_answer: str
    citations: List[Dict[str, Any]]
    citation_verification_status: str  # VERIFIED, PARTIAL, FAILED
    is_grounded: bool
    insufficient_evidence: bool

    # Observability & loop control
    retry_count: int
    max_retries: int
    error: Optional[str]
    telemetry: Dict[str, Any]

