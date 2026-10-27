"""
Research Paper Summarizer – Streamlit application.

Upload a PDF → get a structured brief → see evidence checks.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

import streamlit as st

from pdf_reader import extract_text_by_page, PDFExtractionError
from chunker import chunk_pages, Chunk
from indexer import index_chunks, delete_paper_index
from summarizer import write_brief
from evidence_checker import extract_claims, check_claims, ClaimCheck
from ollama_client import health_check, OllamaError
from config import OLLAMA_MODEL


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Research Paper Summarizer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a polished UI
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* -- Fonts ----------------------------------------------------------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* -- Sidebar --------------------------------------------------------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #1a1a40 50%, #24243e 100%);
    }
    section[data-testid="stSidebar"] * { color: #e0e0e0; }

    /* -- Header ---------------------------------------------------------- */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-header h1 {
        margin: 0; font-size: 2rem; font-weight: 700;
    }
    .main-header p {
        margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.05rem;
    }

    /* -- Cards ----------------------------------------------------------- */
    .brief-card {
        background: linear-gradient(145deg, #f8f9ff 0%, #f0f2ff 100%);
        border-left: 4px solid #667eea;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .brief-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(102,126,234,0.15);
    }
    .brief-card h3 {
        color: #4a5aba; margin: 0 0 0.5rem 0; font-size: 1.1rem;
    }
    .brief-card p { color: #333; margin: 0; line-height: 1.65; }

    /* -- Verdict badges -------------------------------------------------- */
    .verdict-supported {
        background: #d4edda; color: #155724; padding: 3px 12px;
        border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        display: inline-block;
    }
    .verdict-partly {
        background: #fff3cd; color: #856404; padding: 3px 12px;
        border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        display: inline-block;
    }
    .verdict-unsupported {
        background: #f8d7da; color: #721c24; padding: 3px 12px;
        border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        display: inline-block;
    }
    .verdict-contradicted {
        background: #f5c6cb; color: #721c24; padding: 3px 12px;
        border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        display: inline-block;
    }

    /* -- Evidence box ---------------------------------------------------- */
    .evidence-box {
        background: #fafbff;
        border: 1px solid #e0e4f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-top: 0.5rem;
    }
    .evidence-box blockquote {
        border-left: 3px solid #667eea;
        padding-left: 0.75rem;
        color: #555;
        font-style: italic;
    }

    /* -- Stats bar ------------------------------------------------------- */
    .stat-item {
        text-align: center;
        padding: 0.75rem;
    }
    .stat-item .number {
        font-size: 1.6rem; font-weight: 700; color: #667eea;
    }
    .stat-item .label {
        font-size: 0.8rem; color: #888; text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* -- Disclaimer ------------------------------------------------------ */
    .disclaimer {
        background: linear-gradient(135deg, #fff8e1 0%, #fff3cd 100%);
        border: 1px solid #ffc107;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-top: 1.5rem;
        font-size: 0.9rem;
        color: #664d03;
    }

    /* -- Misc ------------------------------------------------------------ */
    div[data-testid="stExpander"] {
        border: 1px solid #e0e4f0;
        border-radius: 10px;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="main-header">
    <h1>📄 Research Paper Summarizer</h1>
    <p>Upload a research paper PDF and get a structured brief with evidence-backed claim verification.</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar – status & settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Status")

    # Ollama health check
    try:
        health_check()
        st.success(f"✅ Ollama running — model `{OLLAMA_MODEL}` available")
        ollama_ok = True
    except OllamaError as e:
        st.error(f"❌ Ollama issue:\n\n{e}")
        ollama_ok = False

    st.markdown("---")
    st.markdown("## 📋 How it works")
    st.markdown(
        "1. **Upload** a PDF with selectable text\n"
        "2. Text is **chunked** (~650 words, ~85 overlap)\n"
        "3. Chunks are **embedded** and stored locally\n"
        "4. An LLM writes a **structured brief**\n"
        "5. Claims are **verified** against source passages"
    )
    st.markdown("---")
    st.markdown(
        "⚠️ This tool does **not** guarantee correctness. "
        "Always inspect the cited source passages, especially "
        "for important results."
    )


# ---------------------------------------------------------------------------
# File uploader
# ---------------------------------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload a research paper (PDF)",
    type=["pdf"],
    help="The PDF must contain selectable text. Scanned image-only PDFs are not supported.",
)

if not uploaded_file:
    st.info("👆 Upload a PDF to get started.")
    st.stop()

if not ollama_ok:
    st.error(
        "Ollama is not available. Please start Ollama and ensure the model "
        f"`{OLLAMA_MODEL}` is pulled before processing papers."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Session-state keys for this file
# ---------------------------------------------------------------------------

file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()

if "current_hash" not in st.session_state or st.session_state.current_hash != file_hash:
    # New file uploaded – reset state
    st.session_state.current_hash = file_hash
    st.session_state.pages = None
    st.session_state.chunks = None
    st.session_state.brief = None
    st.session_state.claim_checks = None
    st.session_state.paper_id = file_hash[:16]


# ---------------------------------------------------------------------------
# Step 1: Extract text
# ---------------------------------------------------------------------------

if st.session_state.pages is None:
    with st.spinner("📖 Extracting text from PDF…"):
        # Save uploaded file to a temp path for PyMuPDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            pages = extract_text_by_page(tmp_path)
            st.session_state.pages = pages
        except PDFExtractionError as e:
            st.error(str(e))
            st.stop()
        finally:
            os.unlink(tmp_path)

pages = st.session_state.pages
total_words = sum(len(t.split()) for _, t in pages)


# ---------------------------------------------------------------------------
# Step 2: Chunk & index
# ---------------------------------------------------------------------------

if st.session_state.chunks is None:
    with st.spinner("🔧 Chunking and indexing…"):
        chunks = chunk_pages(pages)
        st.session_state.chunks = chunks

        # Index in ChromaDB
        index_chunks(st.session_state.paper_id, chunks)

chunks = st.session_state.chunks


# ---------------------------------------------------------------------------
# Stats bar
# ---------------------------------------------------------------------------

cols = st.columns(4)
with cols[0]:
    st.markdown(f'<div class="stat-item"><div class="number">{len(pages)}</div>'
                f'<div class="label">Pages</div></div>', unsafe_allow_html=True)
with cols[1]:
    st.markdown(f'<div class="stat-item"><div class="number">{total_words:,}</div>'
                f'<div class="label">Words</div></div>', unsafe_allow_html=True)
with cols[2]:
    st.markdown(f'<div class="stat-item"><div class="number">{len(chunks)}</div>'
                f'<div class="label">Chunks</div></div>', unsafe_allow_html=True)
with cols[3]:
    st.markdown(f'<div class="stat-item"><div class="number">{OLLAMA_MODEL}</div>'
                f'<div class="label">Model</div></div>', unsafe_allow_html=True)

st.markdown("---")


# ---------------------------------------------------------------------------
# Step 3: Generate brief
# ---------------------------------------------------------------------------

if st.session_state.brief is None:
    st.markdown("### 🧠 Generating Brief…")
    progress_bar = st.progress(0, text="Summarising paper…")

    def brief_progress(current, total):
        progress_bar.progress(
            (current + 1) / total,
            text=f"Summarising chunk {current + 1}/{total}…",
        )

    try:
        brief = write_brief(chunks, progress_callback=brief_progress)
        st.session_state.brief = brief
        progress_bar.empty()
    except OllamaError as e:
        st.error(f"Error during summarisation:\n\n{e}")
        st.stop()

brief = st.session_state.brief


# ---------------------------------------------------------------------------
# Display brief
# ---------------------------------------------------------------------------

st.markdown("## 📝 Paper Brief")

section_icons = {
    "problem": "🎯",
    "method": "🔬",
    "results": "📊",
    "limitations": "⚠️",
    "main_takeaway": "💡",
}
section_titles = {
    "problem": "Problem",
    "method": "Method",
    "results": "Results",
    "limitations": "Limitations",
    "main_takeaway": "Main Takeaway",
}

for key in ["problem", "method", "results", "limitations", "main_takeaway"]:
    icon = section_icons.get(key, "")
    title = section_titles.get(key, key.replace("_", " ").title())
    content = brief.get(key, "—")
    st.markdown(
        f'<div class="brief-card">'
        f'<h3>{icon} {title}</h3>'
        f'<p>{content}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")


# ---------------------------------------------------------------------------
# Step 4: Evidence check
# ---------------------------------------------------------------------------

if st.session_state.claim_checks is None:
    st.markdown("### 🔍 Verifying Claims…")
    check_progress = st.progress(0, text="Extracting claims…")

    try:
        claims = extract_claims(brief)
        if not claims:
            st.warning("Could not extract verifiable claims from the brief.")
            st.session_state.claim_checks = []
        else:
            def check_progress_cb(current, total):
                check_progress.progress(
                    (current + 1) / total,
                    text=f"Checking claim {current + 1}/{total}…",
                )

            results = check_claims(
                claims,
                st.session_state.paper_id,
                pages,
                progress_callback=check_progress_cb,
            )
            st.session_state.claim_checks = results
        check_progress.empty()
    except OllamaError as e:
        st.error(f"Error during claim verification:\n\n{e}")
        st.stop()

claim_checks = st.session_state.claim_checks


# ---------------------------------------------------------------------------
# Display claim checks
# ---------------------------------------------------------------------------

if claim_checks:
    st.markdown("## 🔍 Evidence Check")
    st.caption(
        "Each key claim from the brief is checked against the paper's text. "
        "Quotes marked ✅ were found in the extracted text; quotes marked ⚠️ "
        "could not be verified verbatim."
    )

    for i, cc in enumerate(claim_checks):
        verdict_class = {
            "Supported": "verdict-supported",
            "Partly supported": "verdict-partly",
            "Unsupported": "verdict-unsupported",
            "Contradicted": "verdict-contradicted",
        }.get(cc.verdict, "verdict-unsupported")

        with st.expander(
            f"{'✅' if cc.verdict == 'Supported' else '⚠️' if 'Partly' in cc.verdict else '❌'} "
            f"Claim {i+1}: {cc.claim[:100]}{'…' if len(cc.claim) > 100 else ''}",
            expanded=(cc.verdict != "Supported"),
        ):
            st.markdown(
                f'<span class="{verdict_class}">{cc.verdict}</span>',
                unsafe_allow_html=True,
            )

            st.markdown(f"**Claim:** {cc.claim}")

            if cc.explanation:
                st.markdown(f"**Explanation:** {cc.explanation}")

            if cc.evidence_quote:
                verified_icon = "✅" if cc.quote_verified else "⚠️"
                page_info = f" (page {cc.page_number})" if cc.page_number else ""
                st.markdown(
                    f'<div class="evidence-box">'
                    f'<strong>Evidence {verified_icon}{page_info}:</strong>'
                    f'<blockquote>{cc.evidence_quote}</blockquote>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

st.markdown("---")


# ---------------------------------------------------------------------------
# Download buttons
# ---------------------------------------------------------------------------

st.markdown("## 💾 Download Results")
col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    brief_json = json.dumps(brief, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Download Brief (JSON)",
        data=brief_json,
        file_name="paper_brief.json",
        mime="application/json",
    )

with col_dl2:
    checks_data = [cc.to_dict() for cc in claim_checks]
    checks_json = json.dumps(checks_data, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Download Evidence Checks (JSON)",
        data=checks_json,
        file_name="evidence_checks.json",
        mime="application/json",
    )


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="disclaimer">'
    '<strong>⚠️ Disclaimer:</strong> '
    'This summary is generated by a local language model and is <strong>not guaranteed '
    'to be correct</strong>. The evidence checker flags potential issues but cannot '
    'catch every error. Always inspect the cited source passages, especially for '
    'important results, numbers, and methodological claims.'
    '</div>',
    unsafe_allow_html=True,
)
