"""OCR adapter — local Tesseract fallback when PDF text extraction is insufficient."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

# Pages below this character count are treated as needing OCR.
MIN_EXTRACTED_CHARS = 40
# Alphanumeric ratio below this also triggers OCR (garbage / sparse glyphs).
MIN_ALNUM_RATIO = 0.15


class OCRUnavailableError(RuntimeError):
    """Raised when OCR is required but no runtime OCR binary/provider is usable."""


class OCRProvider(Protocol):
    def extract_pages(self, path: Path) -> list[tuple[int, str]]:
        """Return (page_number, text) pairs for the whole document."""

    def extract_page(self, path: Path, page_number: int) -> str:
        """OCR a single 1-based page."""


def page_needs_ocr(
    text: str,
    *,
    min_chars: int = MIN_EXTRACTED_CHARS,
    min_alnum_ratio: float = MIN_ALNUM_RATIO,
) -> bool:
    """Heuristic: empty/sparse extracted text requires OCR; images alone do not."""
    cleaned = (text or "").strip()
    if len(cleaned) < min_chars:
        return True
    alnum = sum(1 for ch in cleaned if ch.isalnum())
    return (alnum / len(cleaned)) < min_alnum_ratio


def document_needs_ocr(page_texts: list[str]) -> bool:
    """True when every page fails the extractable-text heuristic."""
    if not page_texts:
        return True
    return all(page_needs_ocr(text) for text in page_texts)


class UnavailableOCRProvider:
    """Explicit non-provider: never fabricates OCR success."""

    def extract_pages(self, path: Path) -> list[tuple[int, str]]:
        raise OCRUnavailableError(f"OCR required for {path.name} but no OCR provider is configured")

    def extract_page(self, path: Path, page_number: int) -> str:
        raise OCRUnavailableError(
            f"OCR required for {path.name} page {page_number} but no OCR provider is configured"
        )


class TesseractOCRProvider:
    """Local Tesseract OCR via page rasterization (PyMuPDF → image → pytesseract)."""

    def __init__(self, *, lang: str = "eng+spa", dpi: int = 200) -> None:
        self.lang = lang
        self.dpi = dpi

    def extract_pages(self, path: Path) -> list[tuple[int, str]]:
        self._ensure_runtime()
        import fitz

        document = fitz.open(path)
        pages: list[tuple[int, str]] = []
        try:
            for index in range(1, document.page_count + 1):
                pages.append((index, self._ocr_fitz_page(document, index)))
        finally:
            document.close()
        return pages

    def extract_page(self, path: Path, page_number: int) -> str:
        self._ensure_runtime()
        import fitz

        document = fitz.open(path)
        try:
            if page_number < 1 or page_number > document.page_count:
                raise ValueError(f"Page {page_number} out of range for {path.name}")
            return self._ocr_fitz_page(document, page_number)
        finally:
            document.close()

    def _ensure_runtime(self) -> None:
        if shutil.which("tesseract") is None:
            raise OCRUnavailableError("OCR required but tesseract binary is not installed on PATH")
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError as error:
            raise OCRUnavailableError(
                "OCR required but pytesseract/Pillow are not installed"
            ) from error

    def _ocr_fitz_page(self, document: object, page_number: int) -> str:
        import fitz
        import pytesseract
        from PIL import Image

        assert isinstance(document, fitz.Document)
        page = document.load_page(page_number - 1)
        zoom = self.dpi / 72.0
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        text = pytesseract.image_to_string(image, lang=self.lang) or ""
        return text.strip()


def tesseract_available() -> bool:
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


def default_ocr_provider() -> OCRProvider:
    """Prefer local Tesseract; otherwise an explicit unavailable provider."""
    if tesseract_available():
        return TesseractOCRProvider()
    return UnavailableOCRProvider()
