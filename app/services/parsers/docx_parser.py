from pathlib import Path

from docx import Document

from app.services.parsers.base import BaseParser


class DocxParser(BaseParser):
    def parse(self, file_path: str | Path) -> str:
        document = Document(str(file_path))
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )
