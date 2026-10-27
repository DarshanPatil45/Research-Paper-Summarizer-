"""
PDF text extraction using PyMuPDF (fitz).

Returns a list of (page_number, page_text) tuples.
Detects scanned / image-only PDFs and raises a clear message.
"""

from __future__ import annotations

import fitz  # PyMuPDF


class PDFExtractionError(Exception):
    """Raised when meaningful text cannot be extracted from a PDF."""


def extract_text_by_page(pdf_path: str) -> list[tuple[int, str]]:
    """
    Extract selectable text from each page of a PDF.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.

    Returns
    -------
    list of (page_number, page_text)
        page_number is 1-indexed.

    Raises
    ------
    PDFExtractionError
        If the PDF contains no extractable text (likely scanned / image-only).
    """
    doc = fitz.open(pdf_path)
    pages: list[tuple[int, str]] = []
    total_chars = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # plain UTF-8
        text = text.strip()
        if text:
            pages.append((page_num + 1, text))  # 1-indexed
            total_chars += len(text)

    doc.close()

    if total_chars < 100:
        raise PDFExtractionError(
            "This PDF contains little or no extractable text.\n\n"
            "It may be a scanned document or consist mainly of images. "
            "Please use a PDF with selectable text, or run OCR on the "
            "document first (e.g. with `ocrmypdf`)."
        )

    return pages


def full_text(pages: list[tuple[int, str]]) -> str:
    """Concatenate all page texts into a single string."""
    return "\n\n".join(text for _, text in pages)
