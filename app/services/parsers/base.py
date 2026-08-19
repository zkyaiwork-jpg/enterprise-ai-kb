from abc import ABC, abstractmethod
from pathlib import Path


class BaseParser(ABC):
    """Common contract for document-to-text parsers."""

    @abstractmethod
    def parse(self, file_path: str | Path) -> str:
        """Extract plain text from a document path."""
        raise NotImplementedError
