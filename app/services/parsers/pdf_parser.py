from pathlib import Path

import pymupdf

from app.services.parsers.base import BaseParser


class PdfParser(BaseParser):
    def parse(self, file_path: str | Path) -> str:
        pages: list[str] = []
        with pymupdf.open(str(file_path)) as document:
            for page in document:
                text = page.get_text("text").strip()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)
