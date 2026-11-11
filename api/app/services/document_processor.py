"""
Ingestion ("write path"): extract text → split into chunks → embed and store.

Text is extracted per *section* (a PDF page, or the whole file for other
formats) and chunked section by section, so every chunk keeps the page number
it came from. Citations can then point at the right page.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.vector_store import VectorStoreService
from app.utils.text_processing import clean_text


@dataclass
class Section:
    text: str
    page_number: int | None = None


class UnsupportedFileType(ValueError):
    pass


def _read_text_file(path: Path) -> str:
    # utf-8-sig strips a BOM; replace undecodable bytes instead of failing the whole upload.
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _extract_pdf(path: Path) -> list[Section]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [Section(page.extract_text() or "", page_number=i + 1) for i, page in enumerate(reader.pages)]


def _extract_docx(path: Path) -> list[Section]:
    import docx

    document = docx.Document(str(path))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return [Section("\n".join(parts))]


def _extract_csv(path: Path) -> list[Section]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return []
    header, body = rows[0], rows[1:]
    # "column: value" lines keep each row self-describing after chunking.
    lines = ["; ".join(f"{h}: {v}" for h, v in zip(header, row, strict=False)) for row in body] or [", ".join(header)]
    return [Section("\n".join(lines))]


EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".csv": _extract_csv,
    ".txt": lambda p: [Section(_read_text_file(p))],
    ".md": lambda p: [Section(_read_text_file(p))],
}


class DocumentProcessor:
    def __init__(self, vector_store: VectorStoreService, chunk_size: int = 500, chunk_overlap: int = 50):
        self.vector_store = vector_store
        # Try paragraph, line, sentence, then word boundaries before cutting mid-word.
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        )

    @staticmethod
    def supported_extensions() -> list[str]:
        return sorted(EXTRACTORS)

    def extract_sections(self, file_path: str) -> list[Section]:
        path = Path(file_path)
        extractor = EXTRACTORS.get(path.suffix.lower())
        if extractor is None:
            raise UnsupportedFileType(f"Unsupported file type: '{path.suffix}'")
        sections = [Section(clean_text(s.text), s.page_number) for s in extractor(path)]
        return [s for s in sections if s.text]

    def chunk_sections(self, sections: list[Section]) -> tuple[list[str], list[dict]]:
        chunks: list[str] = []
        metadatas: list[dict] = []
        for section in sections:
            for chunk in self.text_splitter.split_text(section.text):
                chunks.append(chunk)
                metadatas.append({"page_number": section.page_number} if section.page_number else {})
        return chunks, metadatas

    def process_document(self, file_path: str, document_id: str, filename: str) -> int:
        """
        Run the full pipeline and return the number of chunks stored.
        Blocking (parsing + embedding calls); call it from a worker thread.
        Raises ValueError with a user-facing message when the file has no usable text.
        """
        sections = self.extract_sections(file_path)
        if not sections:
            raise ValueError("No text could be extracted from the document (is it a scanned PDF?)")
        chunks, metadatas = self.chunk_sections(sections)
        if not chunks:
            raise ValueError("Document produced no chunks after splitting")
        return self.vector_store.add_documents(chunks, document_id, filename, metadatas)
