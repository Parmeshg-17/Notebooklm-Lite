import re
import unicodedata
from typing import Any, Dict, List


class TextCleaner:
    """
    Cleans raw document text, normalizes unicode punctuation, removes null bytes,
    collapses excessive dots/whitespace, and strips detected running headers/footers.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""

        # Normalize unicode (NFKC)
        cleaned = unicodedata.normalize("NFKC", text)

        # Remove null bytes and non-printable control characters (except tab and newline)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)

        # Normalize curly quotes and dashes
        cleaned = re.sub(r"[\u2018\u2019\u201A\u201B]", "'", cleaned)
        cleaned = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', cleaned)
        cleaned = re.sub(r"[\u2013\u2014\u2015]", "-", cleaned)

        # Collapse table of contents dot leaders (e.g., '. . . . .' -> '...')
        cleaned = re.sub(r"(?:\. ){3,}\.?", "...", cleaned)

        # Normalize whitespace (preserve paragraph newlines)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.splitlines()]

        # Collapse 3+ consecutive newlines to 2
        result_lines = []
        consecutive_empty = 0
        for line in lines:
            if not line:
                consecutive_empty += 1
                if consecutive_empty <= 1:
                    result_lines.append("")
            else:
                consecutive_empty = 0
                result_lines.append(line)

        return "\n".join(result_lines).strip()

    @staticmethod
    def strip_running_headers_footers(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifies repeated top or bottom lines across 3 or more pages
        (common for running headers, book titles, page footers) and removes them.
        """
        if len(pages) < 3:
            return pages

        top_lines = []
        bottom_lines = []
        for p in pages:
            lines = [l.strip() for l in p.get("text", "").splitlines() if l.strip()]
            if lines:
                top_lines.append(lines[0])
                bottom_lines.append(lines[-1])

        # Find repetitive headers
        from collections import Counter
        top_counts = Counter(top_lines)
        bottom_counts = Counter(bottom_lines)

        repeated_headers = {line for line, cnt in top_counts.items() if cnt >= 3 and len(line) < 120}
        repeated_footers = {line for line, cnt in bottom_counts.items() if cnt >= 3 and len(line) < 80}

        cleaned_pages = []
        for p in pages:
            lines = [l.strip() for l in p.get("text", "").splitlines() if l.strip()]
            if lines and lines[0] in repeated_headers:
                lines = lines[1:]
            if lines and lines[-1] in repeated_footers:
                lines = lines[:-1]

            cleaned_pages.append({
                "page_number": p["page_number"],
                "text": "\n".join(lines),
            })

        return cleaned_pages
