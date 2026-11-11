import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.rag.ingestion.pdf_parser import PDFParser
from app.rag.ingestion.text_cleaner import TextCleaner

logger = logging.getLogger("app.rag.document_loader")


class DocumentLoader:
    """
    Loads documents of various formats (PDF, TXT, MD, DOCX) and returns
    structured page-level text data.
    """

    @staticmethod
    def load(file_path: str) -> Tuple[List[Dict[str, Any]], int]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file does not exist: {file_path}")

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            raw_pages, total_pages = PDFParser.extract_pages(str(path))
        elif suffix in (".txt", ".md", ".json", ".csv"):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            raw_pages = [{"page_number": 1, "text": content}]
            total_pages = 1
        elif suffix in (".docx", ".doc"):
            try:
                import docx
                doc = docx.Document(str(path))
                text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                raw_pages = [{"page_number": 1, "text": text}]
                total_pages = 1
            except Exception as e:
                logger.warning(f"python-docx error, falling back to raw read: {e}")
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                raw_pages = [{"page_number": 1, "text": content}]
                total_pages = 1
        else:
            # Fallback text read
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            raw_pages = [{"page_number": 1, "text": content}]
            total_pages = 1

        # Clean pages and strip running headers/footers
        cleaned_pages = []
        for p in raw_pages:
            cleaned_text = TextCleaner.clean_text(p["text"])
            cleaned_pages.append({
                "page_number": p["page_number"],
                "text": cleaned_text,
            })

        final_pages = TextCleaner.strip_running_headers_footers(cleaned_pages)
        return final_pages, total_pages

