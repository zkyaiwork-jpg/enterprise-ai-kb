from pathlib import Path

from app.services.parsers.base import BaseParser
from app.services.parsers.docx_parser import DocxParser
from app.services.parsers.pdf_parser import PdfParser
from app.services.parsers.txt_parser import TxtParser


SUPPORTED_EXTENSIONS = frozenset({".docx", ".txt", ".pdf"})

_PARSERS: dict[str, type[BaseParser]] = {
    ".docx": DocxParser,
    ".txt": TxtParser,
    ".pdf": PdfParser,
}


def get_parser(file_path: str | Path) -> BaseParser:
    extension = Path(file_path).suffix.lower()
    parser_class = _PARSERS.get(extension)
    if parser_class is None:
        raise ValueError(f"不支持的文件格式：{extension or '无扩展名'}")
    return parser_class()
