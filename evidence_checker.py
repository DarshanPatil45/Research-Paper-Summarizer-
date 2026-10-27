"""
Evidence checker – extracts factual claims from the brief and verifies
each claim against the paper's indexed chunks.

Workflow:
  1. Ask the LLM to extract key factual claims from the brief.
  2. For each claim, retrieve relevant chunks via semantic search.
  3. Ask the LLM whether the retrieved evidence supports the claim.
  4. Cross-check any quoted text against the actual extracted page text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Optional

from ollama_client import generate
from indexer import retrieve
from pdf_reader import extract_text_by_page


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ClaimCheck:
    claim: str
    verdict: str          # Supported | Partly supported | Unsupported | Contradicted
    evidence_quote: str   # short quote from the paper
    page_number: int      # page where evidence was found (0 = unknown)
    explanation: str      # LLM reasoning
    quote_verified: bool  # True if the quote was found in extracted text

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_EXTRACT_CLAIMS_PROMPT = """\
Below is a structured brief summarising a research paper.

---
Problem: {problem}
Method: {method}
Results: {results}
Limitations: {limitations}
Main Takeaway: {main_takeaway}
---

Extract 3-6 key factual claims from this brief. Focus on specific, verifiable
statements (numbers, comparisons, method descriptions) rather than vague assertions.

Return ONLY a JSON array of strings, e.g.:
["claim 1", "claim 2", "claim 3"]
"""

_VERIFY_CLAIM_PROMPT = """\
You are verifying whether a claim from a paper summary is supported by the
source text.

CLAIM: {claim}

EVIDENCE PASSAGES (from the paper):
{evidence}

Based ONLY on the evidence above, classify the claim as one of:
- Supported: the evidence clearly confirms the claim
- Partly supported: the evidence partially confirms or the claim oversimplifies
- Unsupported: the evidence does not address the claim
- Contradicted: the evidence directly contradicts the claim

Also provide:
- A short quote (≤ 30 words) from the evidence that is most relevant.
- The page number where that quote appears (from the metadata).
- A brief explanation (1-2 sentences).

Return ONLY valid JSON:
{{
  "verdict": "Supported|Partly supported|Unsupported|Contradicted",
  "quote": "exact short quote",
  "page": <page_number>,
  "explanation": "brief reasoning"
}}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json_array(text: str) -> list[str]:
    """Extract a JSON array of strings from LLM output."""
    try:
        arr = json.loads(text)
        if isinstance(arr, list):
            return [str(x) for x in arr]
    except json.JSONDecodeError:
        pass

    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except json.JSONDecodeError:
            pass

    # Fallback: line-by-line
    claims = []
    for line in text.splitlines():
        line = line.strip().strip("-•*").strip()
        if line and len(line) > 10:
            # Remove leading numbers/quotes
            line = re.sub(r'^[\d.]+\s*', '', line).strip('"').strip("'")
            if line:
                claims.append(line)
    return claims[:6]


def _extract_verify_json(text: str) -> dict:
    """Extract verification JSON from LLM output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return {
        "verdict": "Unsupported",
        "quote": "",
        "page": 0,
        "explanation": "Could not parse verification result.",
    }


def _verify_quote_in_pages(quote: str, page_num: int,
                            pages: list[tuple[int, str]]) -> bool:
    """
    Check if the quote (or a reasonable substring) actually appears
    in the extracted text for the given page.
    """
    if not quote or len(quote) < 5:
        return False

    # Normalise whitespace for comparison
    def norm(s: str) -> str:
        return re.sub(r'\s+', ' ', s.lower().strip())

    norm_quote = norm(quote)

    # Check the specific page first
    for pnum, ptext in pages:
        if pnum == page_num:
            if norm_quote in norm(ptext):
                return True
            # Try a shorter substring (first 40 chars)
            short = norm_quote[:40]
            if len(short) > 10 and short in norm(ptext):
                return True

    # Check adjacent pages (±1) in case page assignment is slightly off
    for pnum, ptext in pages:
        if abs(pnum - page_num) <= 1:
            if norm_quote in norm(ptext):
                return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_claims(brief: dict) -> list[str]:
    """Extract key factual claims from the brief."""
    prompt = _EXTRACT_CLAIMS_PROMPT.format(**brief)
    raw = generate(prompt, temperature=0.1, max_tokens=800)
    claims = _extract_json_array(raw)
    return claims


def check_claims(claims: list[str], paper_id: str,
                 pages: list[tuple[int, str]],
                 progress_callback=None) -> list[ClaimCheck]:
    """
    Verify each claim against the paper.

    Parameters
    ----------
    claims : list of claim strings
    paper_id : identifier for the paper (used for retrieval)
    pages : extracted (page_number, text) list (for quote verification)
    progress_callback : optional callable(current, total)

    Returns
    -------
    list of ClaimCheck
    """
    results: list[ClaimCheck] = []

    for i, claim in enumerate(claims):
        if progress_callback:
            progress_callback(i, len(claims))

        # Retrieve relevant chunks
        hits = retrieve(paper_id, claim, top_k=4)
        if not hits:
            results.append(ClaimCheck(
                claim=claim,
                verdict="Unsupported",
                evidence_quote="",
                page_number=0,
                explanation="No relevant passages found in the paper.",
                quote_verified=False,
            ))
            continue

        # Format evidence for the LLM
        evidence_parts = []
        for h in hits:
            pages_str = f"(pages {h['page_start']}–{h['page_end']})"
            section = f" [{h['section']}]" if h.get("section") else ""
            evidence_parts.append(
                f"{pages_str}{section}\n{h['text'][:1500]}"
            )
        evidence_text = "\n\n---\n\n".join(evidence_parts)

        prompt = _VERIFY_CLAIM_PROMPT.format(
            claim=claim,
            evidence=evidence_text,
        )
        raw = generate(prompt, temperature=0.1, max_tokens=600)
        parsed = _extract_verify_json(raw)

        quote = parsed.get("quote", "")
        page = int(parsed.get("page", 0))
        verdict = parsed.get("verdict", "Unsupported")

        # Validate verdict
        valid_verdicts = {"Supported", "Partly supported",
                          "Unsupported", "Contradicted"}
        if verdict not in valid_verdicts:
            # Best-effort normalisation
            verdict_lower = verdict.lower()
            if "support" in verdict_lower and "partly" in verdict_lower:
                verdict = "Partly supported"
            elif "support" in verdict_lower:
                verdict = "Supported"
            elif "contradict" in verdict_lower:
                verdict = "Contradicted"
            else:
                verdict = "Unsupported"

        # Verify the quote against actual extracted text
        quote_verified = _verify_quote_in_pages(quote, page, pages)

        results.append(ClaimCheck(
            claim=claim,
            verdict=verdict,
            evidence_quote=quote if quote_verified else (
                quote + " [⚠ quote not verified in source text]"
                if quote else ""
            ),
            page_number=page,
            explanation=parsed.get("explanation", ""),
            quote_verified=quote_verified,
        ))

    return results
