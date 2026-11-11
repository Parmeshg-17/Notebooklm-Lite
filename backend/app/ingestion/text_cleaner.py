import re


class TextCleaner:
    @staticmethod
    def clean(text: str) -> str:
        """Clean extracted PDF text while preserving readability."""
        if not text:
            return ""

        # Remove null bytes
        cleaned = text.replace("\x00", "")

        # Normalize unicode quotes and dashes
        cleaned = (
            cleaned.replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2014", " - ")
            .replace("\u2013", " - ")
        )

        # Reconnect words split by hyphen at end of line (e.g. "connec-\ntion" -> "connection")
        cleaned = re.sub(r"(\w+)-\n(\w+)", r"\1\2", cleaned)

        # Collapse dot leaders from table of contents (e.g. ". . . . . ." -> "...")
        cleaned = re.sub(r"(?:\. ){3,}\.?", " ... ", cleaned)
        cleaned = re.sub(r"\.{4,}", "...", cleaned)

        # Normalize line endings
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # Replace excessive whitespace within lines (multiple spaces/tabs to single space)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        # Replace 3 or more consecutive newlines with 2 newlines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()

