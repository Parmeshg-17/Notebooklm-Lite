from typing import Any, Dict, List


class ContextBuilder:
    """Formats retrieved passages into structured context blocks for LLM prompt."""

    @staticmethod
    def build_context(passages: List[Dict[str, Any]]) -> str:
        if not passages:
            return ""

        # Sort by document name, then page number for logical reading order
        sorted_passages = sorted(
            passages,
            key=lambda p: (str(p.get("filename", "")), int(p.get("page_number", 1))),
        )

        blocks = []
        for idx, p in enumerate(sorted_passages, start=1):
            fname = p.get("filename") or "Document"
            page_num = p.get("page_number", 1)
            raw_text = p.get("chunk_text") or p.get("text", "")
            clean_text = "\n".join(line.strip() for line in raw_text.splitlines() if line.strip())
            chunk_id = p.get("chunk_id", "")
            blocks.append(
                f"[Source {idx} - Document: {fname}, Page: {page_num}, ChunkID: {chunk_id}]:\n{clean_text}"
            )

        return "\n\n".join(blocks)

