from pathlib import Path

from app.services.parsers.base import BaseParser


class TxtParser(BaseParser):
    def parse(self, file_path: str | Path) -> str:
        path = Path(file_path)
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            # GB18030 covers common Chinese Windows text files while still
            # surfacing an error for unsupported/binary input.
            return path.read_text(encoding="gb18030")
