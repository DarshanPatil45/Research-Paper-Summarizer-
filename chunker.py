"""
Text chunker – splits extracted PDF text into overlapping chunks with metadata.

Each chunk carries:
  - text         : the chunk body
  - page_start   : first page number contributing to this chunk
  - page_end     : last page number contributing to this chunk
  - section      : best-guess section heading (if detected), else ""
  - chunk_index  : ordinal position in the document
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from config import CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS


@dataclass
class Chunk:
    text: str
    page_start: int
    page_end: int
    section: str = ""
    chunk_index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# Heuristic: lines that look like section headings in academic papers.
_HEADING_RE = re.compile(
    r"^(?:\d+\.?\s+)?"                        # optional numbering
    r"(Abstract|Introduction|Background|Related Work|"
    r"Methodology|Methods?|Approach|"
    r"Experiments?|Evaluation|Results?|"
    r"Discussion|Limitations?|"
    r"Conclusion|Conclusions|Summary|"
    r"Future Work|Acknowledgments?|References|Appendix)",
    re.IGNORECASE,
)


def _detect_section(text: str) -> str:
    """Return the last section heading found before / within this text."""
    for line in reversed(text.splitlines()):
        line = line.strip()
        m = _HEADING_RE.match(line)
        if m:
            return m.group(0).strip()
    return ""


def chunk_pages(pages: list[tuple[int, str]],
                chunk_size: int = CHUNK_SIZE_WORDS,
                overlap: int = CHUNK_OVERLAP_WORDS) -> list[Chunk]:
    """
    Split page-level text into word-count-based overlapping chunks.

    Parameters
    ----------
    pages : list of (page_number, page_text)
    chunk_size : target words per chunk
    overlap : words of overlap between consecutive chunks

    Returns
    -------
    list of Chunk
    """
    # Build a flat list of (word, page_number)
    word_page: list[tuple[str, int]] = []
    for page_num, text in pages:
        words = text.split()
        for w in words:
            word_page.append((w, page_num))

    if not word_page:
        return []

    chunks: list[Chunk] = []
    start = 0
    idx = 0

    while start < len(word_page):
        end = min(start + chunk_size, len(word_page))
        selected = word_page[start:end]
        text = " ".join(w for w, _ in selected)
        page_start = selected[0][1]
        page_end = selected[-1][1]
        section = _detect_section(text)

        chunks.append(Chunk(
            text=text,
            page_start=page_start,
            page_end=page_end,
            section=section,
            chunk_index=idx,
        ))

        # Advance by (chunk_size - overlap) words
        start += max(chunk_size - overlap, 1)
        idx += 1

    return chunks
