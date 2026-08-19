from app.services.parsers.docx_parser import DocxParser

def parse_docx(file_path: str):
    """Backward-compatible wrapper for callers outside the upload service."""
    return DocxParser().parse(file_path)
