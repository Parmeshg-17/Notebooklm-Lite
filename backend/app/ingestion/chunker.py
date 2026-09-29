"""
Page-Preserving Intelligent Chunker.
Splits parsed document pages into chunks while strictly preserving page_start and page_end metadata.
Respects configurable token budgets and overlap.
"""

from dataclasses import dataclass
import re
from typing import List

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ingestion.parser import ParsedPage

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class DocumentChunk:
    chunk_index: int
    page_start: int
    page_end: int
    text: str
    token_count: int


class PagePreservingChunker:
    """
    Chunks documents while maintaining exact page tracking.
    Never splits across document without tagging exact start and end page.
    """

    def __init__(
        self,
        token_budget: int | None = None,
        overlap_tokens: int | None = None,
    ) -> None:
        self.token_budget = token_budget or settings.chunk_token_budget
        self.overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens
        self._tokenizer = None

        try:
            import tiktoken
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            logger.debug("tiktoken not available, using word approximation")

    def count_tokens(self, text: str) -> int:
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        return int(len(text.split()) * 1.33)

    def chunk_pages(self, pages: List[ParsedPage]) -> List[DocumentChunk]:
        """
        Takes page-by-page parsed text and generates sequential chunks.
        Each chunk records:
        - chunk_index
        - page_start (int)
        - page_end (int)
        - text
        """
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        # We first build atomic page units (paragraphs labeled with their originating page)
        units: List[tuple[int, str]] = []  # (page_number, text_snippet)

        for page in pages:
            if not page.text or not page.text.strip():
                continue
            
            # Split page text into paragraphs or sentences
            paras = re.split(r"\n\s*\n", page.text)
            for p in paras:
                p_clean = p.strip()
                if not p_clean:
                    continue
                # If a single paragraph is longer than token budget, split into sentences
                if self.count_tokens(p_clean) > self.token_budget:
                    sentences = re.split(r"(?<=[.!?])\s+", p_clean)
                    for s in sentences:
                        s_clean = s.strip()
                        if s_clean:
                            units.append((page.page_number, s_clean))
                else:
                    units.append((page.page_number, p_clean))

        if not units:
            return []

        # Now group units into chunks according to token budget and overlap
        current_units: List[tuple[int, str]] = []
        current_tokens = 0

        for page_num, text_snippet in units:
            snippet_tokens = self.count_tokens(text_snippet)

            if current_tokens + snippet_tokens > self.token_budget and current_units:
                # Emit chunk
                chunk_text = "\n\n".join([u[1] for u in current_units])
                p_start = current_units[0][0]
                p_end = current_units[-1][0]
                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_idx,
                        page_start=p_start,
                        page_end=p_end,
                        text=chunk_text,
                        token_count=current_tokens,
                    )
                )
                chunk_idx += 1

                # Retain overlap units from end of current chunk
                overlap_units: List[tuple[int, str]] = []
                overlap_toks = 0
                for u in reversed(current_units):
                    u_toks = self.count_tokens(u[1])
                    if overlap_toks + u_toks <= self.overlap_tokens:
                        overlap_units.insert(0, u)
                        overlap_toks += u_toks
                    else:
                        break

                current_units = overlap_units + [(page_num, text_snippet)]
                current_tokens = sum(self.count_tokens(u[1]) for u in current_units)
            else:
                current_units.append((page_num, text_snippet))
                current_tokens += snippet_tokens

        # Final chunk
        if current_units:
            chunk_text = "\n\n".join([u[1] for u in current_units])
            p_start = current_units[0][0]
            p_end = current_units[-1][0]
            chunks.append(
                DocumentChunk(
                    chunk_index=chunk_idx,
                    page_start=p_start,
                    page_end=p_end,
                    text=chunk_text,
                    token_count=current_tokens,
                )
            )

        return chunks
