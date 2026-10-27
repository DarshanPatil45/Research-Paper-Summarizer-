# 📄 PaperLens – AI Research Paper Summarizer

A full-stack **agentic AI** application that reads a research paper PDF and produces a structured,
plain-language brief with evidence-backed claim verification.

**Frontend:** React + TypeScript + Vite + Tailwind CSS  
**Backend:** Python + FastAPI

> ⚠️ **Disclaimer:** This tool does _not_ guarantee a correct summary.
> The evidence checker flags potential issues but cannot catch every error.
> Always inspect the cited source passages, especially for important results.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Drag-and-drop upload** | Upload PDFs via drag-and-drop or file browser |
| **Live progress** | SSE-powered real-time pipeline progress in the UI |
| **PDF text extraction** | Page-by-page extraction via PyMuPDF with scanned-PDF detection |
| **Smart chunking** | ~650-word chunks with ~85-word overlap; page numbers and section headings preserved |
| **Local embeddings** | `all-MiniLM-L6-v2` via Sentence Transformers — no API calls |
| **Vector retrieval** | ChromaDB with per-paper isolation (no cross-paper evidence leakage) |
| **Structured brief** | Five sections: Problem, Method, Results, Limitations, Main Takeaway |
| **Evidence checker** | Key claims verified against source text with page numbers and quotes |
| **Quote verification** | Quotes are cross-checked against extracted text; unverified quotes are flagged |
| **JSON export** | Download the brief and evidence checks as JSON |
| **Fully local** | No paid APIs, no data leaves your machine |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Ollama** — [install from ollama.com](https://ollama.com)

### 1. Clone & set up the Python backend

```bash
cd Research-Paper-Summarizer
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Pull the language model

```bash
ollama pull llama3.2:3b
```

### 3. Start Ollama (if not already running)

```bash
ollama serve
```

### 4. Generate the sample PDF (optional)

```bash
python create_sample_pdf.py
```

This creates `sample_papers/synthetic_sample.pdf` — a clearly labelled synthetic paper for testing.

### 5. Start the FastAPI backend

```bash
source venv/bin/activate          # if not already active
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at **http://localhost:8000**  
API docs available at **http://localhost:8000/docs**

### 6. Start the React frontend

In a **new terminal**:

```bash
cd frontend
npm install          # first time only
npm run dev
```

Frontend runs at **http://localhost:5173**

Open **http://localhost:5173** in your browser, upload a PDF, and click **Analyse Paper**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               React Frontend (Vite + Tailwind)                   │
│  • Drag-and-drop upload  • SSE progress stream  • Results UI    │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP / SSE
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (api.py)                      │
│  POST /api/analyze  GET /api/stream/{id}  GET /api/result/{id}  │
└──────┬──────────────────────────────────────────────────────────┘
       │ background thread
       ▼
┌──────────────┐   ┌───────────┐   ┌──────────────────────────────┐
│  PDF Reader  │──▶│  Chunker  │──▶│ Indexer (Embeddings+ChromaDB)│
│  (PyMuPDF)   │   │(word-based│   │ sentence-transformers         │
└──────────────┘   └───────────┘   └──────────────┬───────────────┘
                                                   │
                   ┌───────────────────────────────┤
                   ▼                               ▼
           ┌──────────────┐              ┌──────────────────┐
           │ Brief Writer │              │ Evidence Checker  │
           │  (Ollama LLM)│              │ (Retrieval + LLM) │
           └──────────────┘              └──────────────────┘
```

### File overview

| File/Dir | Purpose |
|----------|---------|
| `api.py` | FastAPI app with upload, SSE stream, result, and sample endpoints |
| `pdf_reader.py` | PDF text extraction with PyMuPDF |
| `chunker.py` | Word-count-based overlapping text chunker |
| `indexer.py` | Sentence Transformers embeddings + ChromaDB |
| `summarizer.py` | LLM-based brief writer (single-pass or map-combine) |
| `evidence_checker.py` | Claim extraction, retrieval, and verification |
| `ollama_client.py` | Thin Ollama REST API wrapper with health checks |
| `config.py` | Shared constants (chunk size, model name, etc.) |
| `create_sample_pdf.py` | Generates a synthetic sample paper |
| `frontend/` | React + TypeScript + Vite frontend |
| `frontend/src/App.tsx` | Main app shell and state machine |
| `frontend/src/components/` | UploadZone, ProgressPanel, BriefPanel, EvidencePanel |
| `frontend/src/hooks/useAnalysis.ts` | Upload + SSE streaming hook |

---

## 🔧 How Chunking and Retrieval Work

### Chunking strategy

The paper's extracted text is split into overlapping chunks:

- **Target chunk size:** ~650 words (configurable, range 500–800)
- **Overlap:** ~85 words between consecutive chunks (configurable, range 75–100)
- **Metadata per chunk:** start page, end page, detected section heading, chunk index

The overlap ensures that sentences split across chunk boundaries are captured in at
least one chunk. Section headings are detected with a regex heuristic.

### Retrieval

Each chunk is embedded using `all-MiniLM-L6-v2` (384-dimensional vectors) and stored
in a **ChromaDB** collection specific to the uploaded paper.

**Per-paper isolation:** Each paper gets its own ChromaDB collection (keyed by a SHA-256
hash of the file content), so evidence from one paper never leaks into another.

---

## 🔍 Faithfulness Check: What It Can and Cannot Do

### What it does

- **Extracts 3–6 key factual claims** from the generated brief
- **Retrieves relevant source passages** for each claim via semantic search
- **Classifies each claim** as Supported, Partly Supported, Unsupported, or Contradicted
- **Provides a quote and page number** for the evidence
- **Cross-checks the quote** against the actual extracted text on that page

### What it cannot guarantee

- **Semantic correctness:** The LLM might misinterpret nuanced statements.
- **Completeness:** Not every claim is checked — only the 3–6 most prominent ones.
- **Paraphrasing detection:** Subtle distortions may not be caught.
- **Numerical precision:** Semantic similarity, not arithmetic verification.

**Bottom line:** The evidence checker is a helpful safety net, not a guarantee.

---

## ❓ Jury Questions

### 1. How does it handle papers longer than the model's context window?

The app uses a **map-combine** strategy:

1. **Map step:** Each chunk (~650 words) is summarised independently by the LLM.
   This ensures no single prompt exceeds the context window.
2. **Combine step:** The chunk summaries are concatenated and sent to the LLM in a
   single prompt that asks for the final structured brief.

For short papers (≤ 3,000 words total), the entire text is sent in one prompt.

This design means the LLM never sees the full paper at once for long documents.
The chunk overlap (85 words) partially mitigates missed cross-section connections.

### 2. How does it catch a misstated result?

The evidence checker works in three stages:

1. **Claim extraction:** The LLM identifies specific, verifiable claims from the brief
   (e.g., "AGP achieves a 1.8× training speedup on CIFAR-100 with ResNet-50").
2. **Semantic retrieval:** Each claim is embedded and matched against the paper's chunks.
   If the paper says "1.6× speedup" but the brief says "2×", the relevant chunk
   (containing the actual number) will likely be retrieved.
3. **LLM verdict:** The LLM is shown the claim and the retrieved passages side-by-side
   and asked to classify support level. When the numbers don't match, it should classify
   the claim as "Partly supported" or "Contradicted."

Additionally, **quote verification** cross-checks the LLM's cited quote against the
actual page text. Fabricated or altered quotes are flagged with a warning.

**Limitations:** This approach is probabilistic. It works best for catching gross
misstatements and ensuring quoted passages actually exist in the source.

---

## 🔄 Error Handling

| Scenario | What happens |
|----------|-------------|
| Ollama not running | Header shows a red banner with `ollama serve` instructions |
| Model not pulled | Error message with `ollama pull llama3.2:3b` command |
| Scanned / image PDF | Descriptive error suggesting OCR preprocessing |
| LLM timeout | Error message with suggestion to try shorter input |
| Empty PDF | Detected during extraction with helpful message |
| Backend unreachable | Frontend shows offline indicator; upload button disabled |

---

## ⚙️ Configuration

Edit `config.py` to adjust:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model to use |
| `CHUNK_SIZE_WORDS` | 650 | Target words per chunk |
| `CHUNK_OVERLAP_WORDS` | 85 | Overlap between chunks |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `TOP_K_RETRIEVAL` | 5 | Chunks retrieved per query |
| `MAX_CHUNK_TOKENS_FOR_CONTEXT` | 3000 | Word threshold for single-pass vs. map-combine |

---

## 📁 Sample Paper

The included sample is a **synthetic** research paper: `sample_papers/synthetic_sample.pdf`.

- **Title:** "Adaptive Gradient Pruning for Efficient Training of Deep Neural Networks"
- **Content:** Realistic structure with abstract, introduction, methods, experiments, limitations.
- **Label:** Clearly marked as `[SYNTHETIC PAPER — for demonstration purposes only]`

Generate it with:

```bash
python create_sample_pdf.py
```

---

## 📜 License

This project is provided as-is for educational and research purposes.
