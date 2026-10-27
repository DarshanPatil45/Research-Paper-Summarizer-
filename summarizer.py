"""
Brief writer – produces a structured summary of a research paper.

Strategy for long papers:
  1. Summarise each chunk individually (map step).
  2. Combine chunk summaries into a single set of notes.
  3. Write the final brief from the combined notes.

For short papers (≤ MAX_CHUNK_TOKENS_FOR_CONTEXT words), the paper text
is sent directly.
"""

from __future__ import annotations

import json
import re
from chunker import Chunk
from ollama_client import generate
from config import MAX_CHUNK_TOKENS_FOR_CONTEXT


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_BRIEF = (
    "You are a research-paper summariser. Write in plain language that a "
    "technically literate reader can follow. Be accurate and concise. "
    "Do NOT invent facts. If you are unsure, say so."
)

_SINGLE_PASS_PROMPT = """\
Below is text extracted from a research paper.

---
{text}
---

Write a structured brief with exactly these five sections:

1. **Problem** – What problem does the paper address and why does it matter?
2. **Method** – What approach or technique do the authors use?
3. **Results** – What are the main findings or contributions?
4. **Limitations** – What limitations do the authors acknowledge or that are apparent?
5. **Main Takeaway** – One-sentence plain-language takeaway.

Return ONLY valid JSON with keys: problem, method, results, limitations, main_takeaway.
Each value should be a string (1-3 sentences).
"""

_CHUNK_SUMMARY_PROMPT = """\
Below is a chunk of text from a research paper (pages {page_start}–{page_end}).

---
{text}
---

Write a concise 3–5 sentence summary of the key information in this chunk.
Focus on facts, numbers, methods, and findings. Do not add opinions.
"""

_COMBINE_PROMPT = """\
Below are summaries of consecutive chunks from a single research paper.

---
{notes}
---

Combine these into a structured brief with exactly five sections:

1. **Problem** – What problem does the paper address and why does it matter?
2. **Method** – What approach or technique do the authors use?
3. **Results** – What are the main findings or contributions?
4. **Limitations** – What limitations do the authors acknowledge or that are apparent?
5. **Main Takeaway** – One-sentence plain-language takeaway.

Return ONLY valid JSON with keys: problem, method, results, limitations, main_takeaway.
Each value should be a string (1-3 sentences).
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from LLM output."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON block in markdown fences
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find the outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    # Fallback: return raw text in all fields
    return {
        "problem": text,
        "method": "",
        "results": "",
        "limitations": "",
        "main_takeaway": "",
    }


def _word_count(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def summarise_chunks_individually(chunks: list[Chunk],
                                  progress_callback=None) -> list[str]:
    """Map step: summarise each chunk independently."""
    notes: list[str] = []
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(i, len(chunks))
        prompt = _CHUNK_SUMMARY_PROMPT.format(
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            text=chunk.text[:6000],  # safety trim
        )
        summary = generate(prompt, system=_SYSTEM_BRIEF, temperature=0.2)
        notes.append(summary)
    return notes


def write_brief(chunks: list[Chunk], progress_callback=None) -> dict:
    """
    Produce the final five-section brief.

    Returns a dict with keys:
      problem, method, results, limitations, main_takeaway
    """
    total_words = sum(_word_count(c.text) for c in chunks)

    if total_words <= MAX_CHUNK_TOKENS_FOR_CONTEXT:
        # Short paper → single-pass
        full_text = "\n\n".join(c.text for c in chunks)
        prompt = _SINGLE_PASS_PROMPT.format(text=full_text[:12000])
        raw = generate(prompt, system=_SYSTEM_BRIEF, temperature=0.2,
                       max_tokens=1500)
        return _extract_json(raw)
    else:
        # Long paper → map-combine
        notes = summarise_chunks_individually(chunks, progress_callback)
        combined = "\n\n---\n\n".join(
            f"[Chunk {i+1}] {n}" for i, n in enumerate(notes)
        )
        # If combined notes are still huge, truncate
        combined = combined[:12000]
        prompt = _COMBINE_PROMPT.format(notes=combined)
        raw = generate(prompt, system=_SYSTEM_BRIEF, temperature=0.2,
                       max_tokens=1500)
        return _extract_json(raw)
