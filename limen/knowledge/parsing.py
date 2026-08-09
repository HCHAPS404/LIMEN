"""Document text extraction. PDF via PyMuPDF; OCR only when text is insufficient."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from limen.knowledge.ocr import (
    OCRProvider,
    OCRUnavailableError,
    default_ocr_provider,
    document_needs_ocr,
    page_needs_ocr,
)

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".text"}


@dataclass(frozen=True)
class ParsedPage:
    page: int | None
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    pages: list[ParsedPage]
    parser: str
    ocr_applied: bool = False


def assert_supported_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type {suffix!r}. Supported: {sorted(SUPPORTED_SUFFIXES)}"
        )
    return suffix


def parse_document(
    path: Path,
    *,
    filename: str,
    ocr: OCRProvider | None = None,
) -> ParsedDocument:
    suffix = assert_supported_filename(filename)
    if suffix == ".pdf":
        return _parse_pdf(path, ocr=ocr or default_ocr_provider())
    return _parse_text(path)


def _parse_text(path: Path) -> ParsedDocument:
    text = path.read_text(encoding="utf-8", errors="replace")
    return ParsedDocument(pages=[ParsedPage(page=1, text=text)], parser="plain-text")


def _parse_pdf(path: Path, *, ocr: OCRProvider) -> ParsedDocument:
    try:
        import fitz  # PyMuPDF
    except ImportError as error:
        raise RuntimeError("PyMuPDF is required to parse PDF documents") from error

    document = fitz.open(path)
    extracted: list[ParsedPage] = []
    try:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            extracted.append(ParsedPage(page=index, text=text))
    finally:
        document.close()

    if not document_needs_ocr([page.text for page in extracted]):
        # Keep native text; do not OCR merely because the PDF contains images.
        return ParsedDocument(pages=extracted, parser="pymupdf", ocr_applied=False)

    # OCR only pages that fail the extractable-text heuristic.
    merged: list[ParsedPage] = []
    ocr_applied = False
    try:
        for page in extracted:
            assert page.page is not None
            if page_needs_ocr(page.text):
                ocr_text = ocr.extract_page(path, page.page)
                merged.append(ParsedPage(page=page.page, text=ocr_text))
                ocr_applied = True
            else:
                merged.append(page)
    except OCRUnavailableError:
        raise

    if not any(page.text.strip() for page in merged):
        raise ValueError("PDF produced no extractable text and OCR returned empty")
    return ParsedDocument(
        pages=merged,
        parser="pymupdf+ocr" if ocr_applied else "pymupdf",
        ocr_applied=ocr_applied,
    )
