import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pymupdf

logger = logging.getLogger("app.rag.pdf_parser")


class PDFParser:
    @staticmethod
    def extract_pages(file_path: str) -> Tuple[List[Dict[str, Any]], int]:
        """
        Extract text from PDF page-by-page using PyMuPDF.
        Preserves 1-indexed page numbering.
        Returns:
            (pages_list, total_pages)
            where each item in pages_list is:
            {"page_number": int, "text": str}
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        pages: List[Dict[str, Any]] = []
        try:
            doc = pymupdf.open(str(path))
            total_pages = len(doc)

            for page_idx in range(total_pages):
                page = doc[page_idx]
                text = page.get_text() or ""
                pages.append({
                    "page_number": page_idx + 1,  # 1-indexed page number
                    "text": text,
                })

            doc.close()
            return pages, total_pages
        except Exception as e:
            logger.error(f"Failed to extract PDF {file_path}: {e}")
            raise RuntimeError(f"PDF extraction error: {e}") from e

