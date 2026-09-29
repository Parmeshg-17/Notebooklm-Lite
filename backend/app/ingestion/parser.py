"""
Document Parser — parses PDF, Markdown, and plain-text documents page-by-page.
Preserves page numbers throughout parsing and ingestion.
"""

from dataclasses import dataclass
import io
import re
from typing import List

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedPage:
    page_number: int
    text: str
    is_ocr: bool = False


@dataclass
class ParsedDocument:
    filename: str
    page_count: int
    pages: List[ParsedPage]


class DocumentParser:
    """Parses PDF, Markdown, and TXT files into page-by-page structured representations."""

    def parse_bytes(self, content: bytes, filename: str) -> ParsedDocument:
        ext = filename.lower().split(".")[-1] if "." in filename else "txt"

        if ext == "pdf":
            return self._parse_pdf(content, filename)
        elif ext in ("md", "markdown"):
            return self._parse_markdown(content, filename)
        elif ext in ("txt", "text"):
            return self._parse_text(content, filename)
        else:
            # Fallback to UTF-8 text interpretation
            return self._parse_text(content, filename)

    def _parse_pdf(self, content: bytes, filename: str) -> ParsedDocument:
        pages: List[ParsedPage] = []

        try:
            import pymupdf  # PyMuPDF
            doc = pymupdf.open(stream=io.BytesIO(content), filetype="pdf")
            total_pages = len(doc)

            for page_idx in range(total_pages):
                page_num = page_idx + 1
                page = doc[page_idx]
                text = page.get_text("text") or ""
                text = text.strip()
                is_ocr = False

                # Check if page is scanned or near-empty
                if len(text) < 40 and len(page.get_images()) > 0:
                    ocr_text = self._try_ocr_pdf_page(page)
                    if ocr_text and len(ocr_text) > len(text):
                        text = ocr_text
                        is_ocr = True

                pages.append(ParsedPage(page_number=page_num, text=text, is_ocr=is_ocr))

            doc.close()
            logger.info("Parsed PDF successfully", filename=filename, pages=total_pages)
            return ParsedDocument(filename=filename, page_count=len(pages), pages=pages)

        except Exception as e:
            logger.warning("PyMuPDF failed, falling back to pypdf", error=str(e), filename=filename)
            return self._parse_pdf_fallback_pypdf(content, filename)

    def _parse_pdf_fallback_pypdf(self, content: bytes, filename: str) -> ParsedDocument:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        total_pages = len(reader.pages)
        pages: List[ParsedPage] = []

        for idx, p in enumerate(reader.pages):
            text = (p.extract_text() or "").strip()
            pages.append(ParsedPage(page_number=idx + 1, text=text))

        return ParsedDocument(filename=filename, page_count=total_pages, pages=pages)

    def _try_ocr_pdf_page(self, page) -> str:
        """Attempt OCR on a PDF page pixmap if pytesseract is installed."""
        try:
            import pytesseract
            from PIL import Image

            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            logger.debug("OCR not available or failed", error=str(e))
            return ""

    def _parse_markdown(self, content: bytes, filename: str) -> ParsedDocument:
        """
        Parses Markdown documents.
        Splits by explicit page separators (e.g. '---' or '<!-- pagebreak -->')
        or major section headers ('# ') into virtual pages of ~400-600 words.
        """
        text = content.decode("utf-8", errors="replace")
        
        # Check for explicit page separators
        if "<!-- pagebreak -->" in text:
            raw_pages = text.split("<!-- pagebreak -->")
        elif "\n---\n" in text:
            raw_pages = text.split("\n---\n")
        else:
            # Segment by Markdown H1/H2 headers or paragraph chunks
            raw_pages = self._paginate_text_by_headers(text)

        pages: List[ParsedPage] = []
        for idx, page_text in enumerate(raw_pages, start=1):
            clean_text = page_text.strip()
            if clean_text:
                pages.append(ParsedPage(page_number=idx, text=clean_text))

        if not pages:
            pages = [ParsedPage(page_number=1, text=text.strip())]

        return ParsedDocument(filename=filename, page_count=len(pages), pages=pages)

    def _parse_text(self, content: bytes, filename: str) -> ParsedDocument:
        """Parses plain-text files into pages of ~500 words preserving natural paragraphs."""
        text = content.decode("utf-8", errors="replace")
        paragraphs = text.split("\n\n")

        pages: List[ParsedPage] = []
        current_page_paragraphs: List[str] = []
        current_word_count = 0
        page_num = 1

        for para in paragraphs:
            para_words = len(para.split())
            if current_word_count + para_words > 450 and current_page_paragraphs:
                pages.append(
                    ParsedPage(
                        page_number=page_num,
                        text="\n\n".join(current_page_paragraphs).strip(),
                    )
                )
                page_num += 1
                current_page_paragraphs = [para]
                current_word_count = para_words
            else:
                current_page_paragraphs.append(para)
                current_word_count += para_words

        if current_page_paragraphs:
            pages.append(
                ParsedPage(
                    page_number=page_num,
                    text="\n\n".join(current_page_paragraphs).strip(),
                )
            )

        if not pages:
            pages = [ParsedPage(page_number=1, text="")]

        return ParsedDocument(filename=filename, page_count=len(pages), pages=pages)

    def _paginate_text_by_headers(self, text: str) -> List[str]:
        """Split text around Markdown headers, grouping into ~400-500 word blocks."""
        sections = re.split(r"(?=(?:\r?\n|^)#{1,2}\s)", text)
        pages: List[str] = []
        current_block: List[str] = []
        current_words = 0

        for sec in sections:
            sec_words = len(sec.split())
            if current_words + sec_words > 500 and current_block:
                pages.append("".join(current_block))
                current_block = [sec]
                current_words = sec_words
            else:
                current_block.append(sec)
                current_words += sec_words

        if current_block:
            pages.append("".join(current_block))

        return pages or [text]
