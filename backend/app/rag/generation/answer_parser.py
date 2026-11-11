import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("app.rag.answer_parser")


class GroundedCitationItem(BaseModel):
    claim: str = ""
    document_id: str = ""
    filename: str = ""
    page_number: int = 1
    chunk_id: str = ""
    excerpt: str = ""

    # Compatibility aliases
    documentId: Optional[str] = None
    documentName: Optional[str] = None
    pageNumber: Optional[int] = None
    relevanceScore: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.documentId and self.document_id:
            self.documentId = self.document_id
        if not self.documentName and self.filename:
            self.documentName = self.filename
        if self.pageNumber is None:
            self.pageNumber = self.page_number


class ParsedGenerationResult(BaseModel):
    answer: str
    citations: List[GroundedCitationItem] = Field(default_factory=list)
    supporting_claims: List[str] = Field(default_factory=list)
    insufficient_evidence: bool = False
    limitations: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0


class AnswerParser:
    @staticmethod
    def parse_raw_response(raw_text: str, candidate_chunks: List[Dict[str, Any]]) -> ParsedGenerationResult:
        if not raw_text or not raw_text.strip():
            return ParsedGenerationResult(
                answer="I couldn't find sufficient supporting information in your uploaded documents to answer this question.",
                insufficient_evidence=True,
            )

        clean_text = raw_text.strip()

        # Try to extract JSON object
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
        if json_match:
            candidate_json = json_match.group(1)
        else:
            cand_brace = re.search(r"(\{.*\})", clean_text, re.DOTALL)
            candidate_json = cand_brace.group(1) if cand_brace else clean_text

        try:
            data = json.loads(candidate_json)
            ans = data.get("answer", clean_text)
            cits = data.get("citations", [])
            claims = data.get("supporting_claims", [])
            insufficient = bool(data.get("insufficient_evidence", False))
            limitations = data.get("limitations")

            parsed_citations = []
            chunk_by_page = {c.get("page_number"): c for c in candidate_chunks if c.get("page_number")}
            default_fname = ""
            default_doc_id = ""
            for c in candidate_chunks:
                if c.get("filename") and not default_fname:
                    default_fname = c.get("filename")
                if c.get("document_id") and not default_doc_id:
                    default_doc_id = str(c.get("document_id"))

            for c in cits:
                if isinstance(c, dict):
                    page_num = int(c.get("page_number") or c.get("pageNumber", 1))
                    matched_chunk = chunk_by_page.get(page_num, {})
                    c_doc_id = str(c.get("document_id") or c.get("documentId") or matched_chunk.get("document_id") or default_doc_id)
                    c_fname = str(c.get("filename") or c.get("documentName") or matched_chunk.get("filename") or default_fname or "Document")
                    c_chunk_id = str(c.get("chunk_id") or c.get("id") or matched_chunk.get("chunk_id") or "")
                    parsed_citations.append(
                        GroundedCitationItem(
                            claim=c.get("claim", ""),
                            document_id=c_doc_id,
                            filename=c_fname,
                            page_number=page_num,
                            chunk_id=c_chunk_id,
                            excerpt=str(c.get("excerpt", "")),
                        )
                    )

            return ParsedGenerationResult(
                answer=ans,
                citations=parsed_citations,
                supporting_claims=claims,
                insufficient_evidence=insufficient,
                limitations=limitations,
            )
        except Exception:
            # Model returned plain prose markdown
            is_refusal = (
                "insufficient" in clean_text.lower()
                or "couldn't find" in clean_text.lower()
                or "cannot be found" in clean_text.lower()
                or "do not contain" in clean_text.lower()
            )
            extracted_cits = []
            if not is_refusal and candidate_chunks:
                from app.rag.citations.citation_extractor import CitationExtractor
                extracted_cits = CitationExtractor.extract_citations([], clean_text, candidate_chunks)
                if not extracted_cits:
                    # Associate top candidate chunks as grounded citations
                    for c in candidate_chunks[:3]:
                        extracted_cits.append(
                            GroundedCitationItem(
                                claim=clean_text[:120],
                                document_id=str(c.get("document_id", "")),
                                filename=str(c.get("filename", "Document")),
                                page_number=int(c.get("page_number", 1)),
                                chunk_id=str(c.get("chunk_id", "")),
                                excerpt=str(c.get("chunk_text") or c.get("text", ""))[:280],
                            )
                        )

            return ParsedGenerationResult(
                answer=clean_text,
                citations=extracted_cits,
                insufficient_evidence=is_refusal,
            )

