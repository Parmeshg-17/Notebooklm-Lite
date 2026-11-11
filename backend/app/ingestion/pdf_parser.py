from pathlib import Path
from typing import Dict, List, Tuple
import pymupdf


class PDFParser:
    @staticmethod
    def extract_pages(file_path: str) -> Tuple[List[Dict[str, int | str]], int]:
        """
        Extract text from PDF page by page.
        Returns:
            (pages_list, total_pages)
            where each item in pages_list is:
            {"page_number": int (1-indexed), "text": str}
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found at path: {file_path}")

        # Check if plain text file
        if path.suffix.lower() in (".txt", ".md", ".csv", ".json"):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return [{"page_number": 1, "text": content}], 1

        pages: List[Dict[str, int | str]] = []
        try:
            doc = pymupdf.open(str(path))
            total_pages = len(doc)

            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_text = page.get_text("text") or ""
                pages.append({
                    "page_number": page_idx + 1,  # 1-indexed for citations
                    "text": page_text,
                })

            doc.close()
            return pages, total_pages
        except Exception as e:
            raise RuntimeError(f"Failed to parse document: {str(e)}") from e

