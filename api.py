"""
Research Paper Summarizer – FastAPI backend.

Endpoints:
  POST /api/analyze        – Upload a PDF; returns a job ID.
  GET  /api/stream/{job_id} – SSE stream of progress events.
  GET  /api/result/{job_id} – Fetch the final JSON result.
  GET  /api/status          – Ollama + model health check.
  GET  /api/sample          – Download the synthetic sample PDF.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from pdf_reader import extract_text_by_page, PDFExtractionError
from chunker import chunk_pages
from indexer import index_chunks
from summarizer import write_brief
from evidence_checker import extract_claims, check_claims
from ollama_client import health_check, OllamaError
from config import OLLAMA_MODEL

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Research Paper Summarizer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory job store  (job_id -> {status, events, result, error})
# ---------------------------------------------------------------------------

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()

SAMPLE_PDF = Path(__file__).parent / "sample_papers" / "synthetic_sample.pdf"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_job(job_id: str):
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "pending",
            "events": [],
            "result": None,
            "error": None,
        }


def _push_event(job_id: str, etype: str, message: str, data: dict | None = None):
    with _jobs_lock:
        event = {"type": etype, "message": message, "data": data or {}, "ts": time.time()}
        _jobs[job_id]["events"].append(event)


def _mark_done(job_id: str, result: dict):
    with _jobs_lock:
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["result"] = result


def _mark_error(job_id: str, error: str):
    with _jobs_lock:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = error


# ---------------------------------------------------------------------------
# Background analysis worker
# ---------------------------------------------------------------------------

def _run_analysis(job_id: str, pdf_bytes: bytes, filename: str):
    """Run the full pipeline in a background thread."""
    try:
        # Step 1: Extract text
        _push_event(job_id, "step", "Extracting text from PDF...", {"step": 1, "total": 5})
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            pages = extract_text_by_page(tmp_path)
        except PDFExtractionError as e:
            _mark_error(job_id, str(e))
            return
        finally:
            os.unlink(tmp_path)

        total_words = sum(len(t.split()) for _, t in pages)
        _push_event(job_id, "extracted", "Text extracted.", {
            "pages": len(pages),
            "words": total_words,
        })

        # Step 2: Chunk & Index
        _push_event(job_id, "step", "Chunking and indexing...", {"step": 2, "total": 5})
        paper_id = hashlib.sha256(pdf_bytes).hexdigest()[:16]
        chunks = chunk_pages(pages)
        index_chunks(paper_id, chunks)
        _push_event(job_id, "indexed", "Indexed chunks.", {"chunks": len(chunks)})

        # Step 3: Write brief
        _push_event(job_id, "step", "Generating paper brief...", {"step": 3, "total": 5})

        def brief_progress(current: int, total: int):
            _push_event(job_id, "brief_progress",
                        f"Summarising chunk {current + 1}/{total}...",
                        {"current": current + 1, "total": total})

        try:
            brief = write_brief(chunks, progress_callback=brief_progress)
        except OllamaError as e:
            _mark_error(job_id, f"Ollama error during summarisation: {e}")
            return

        _push_event(job_id, "brief_done", "Brief generated.", brief)

        # Step 4: Extract claims
        _push_event(job_id, "step", "Extracting key claims...", {"step": 4, "total": 5})
        try:
            claims = extract_claims(brief)
        except OllamaError as e:
            _mark_error(job_id, f"Ollama error during claim extraction: {e}")
            return

        _push_event(job_id, "claims_extracted", f"Extracted {len(claims)} claims.", {
            "count": len(claims)
        })

        # Step 5: Check claims
        _push_event(job_id, "step", "Verifying claims against source...", {"step": 5, "total": 5})

        def check_progress(current: int, total: int):
            _push_event(job_id, "check_progress",
                        f"Checking claim {current + 1}/{total}...",
                        {"current": current + 1, "total": total})

        try:
            claim_checks = check_claims(claims, paper_id, pages,
                                        progress_callback=check_progress)
        except OllamaError as e:
            _mark_error(job_id, f"Ollama error during claim checking: {e}")
            return

        result = {
            "filename": filename,
            "pages": len(pages),
            "words": total_words,
            "chunks": len(chunks),
            "model": OLLAMA_MODEL,
            "brief": brief,
            "claim_checks": [cc.to_dict() for cc in claim_checks],
        }
        _mark_done(job_id, result)
        _push_event(job_id, "done", "Analysis complete.", {})

    except Exception as e:
        _mark_error(job_id, f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/status")
def get_status():
    """Ollama + model health check."""
    try:
        health_check()
        return {"ok": True, "model": OLLAMA_MODEL}
    except OllamaError as e:
        return {"ok": False, "error": str(e), "model": OLLAMA_MODEL}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """Upload a PDF and start the analysis pipeline."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    job_id = hashlib.sha256(pdf_bytes + file.filename.encode()).hexdigest()[:24]
    _new_job(job_id)

    t = threading.Thread(
        target=_run_analysis,
        args=(job_id, pdf_bytes, file.filename),
        daemon=True,
    )
    t.start()

    return {"job_id": job_id}


@app.get("/api/stream/{job_id}")
async def stream_events(job_id: str):
    """SSE stream of progress events for a job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_generator():
        sent = 0
        while True:
            with _jobs_lock:
                job = _jobs.get(job_id)
                if job is None:
                    break
                new_events = job["events"][sent:]
                status = job["status"]

            for ev in new_events:
                data = json.dumps(ev, ensure_ascii=False)
                yield f"data: {data}\n\n"
                sent += 1

            if status in ("done", "error"):
                final = json.dumps({"type": "terminal", "status": status})
                yield f"data: {final}\n\n"
                break

            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/result/{job_id}")
def get_result(job_id: str):
    """Return the final analysis result."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] == "error":
        raise HTTPException(status_code=500, detail=job["error"])
    if job["status"] != "done":
        raise HTTPException(status_code=202, detail="Analysis still in progress.")
    return JSONResponse(content=job["result"])


@app.get("/api/sample")
def download_sample():
    """Download the synthetic sample PDF."""
    if not SAMPLE_PDF.exists():
        raise HTTPException(
            status_code=404,
            detail="Sample PDF not found. Run: python create_sample_pdf.py",
        )
    return FileResponse(
        path=str(SAMPLE_PDF),
        media_type="application/pdf",
        filename="synthetic_sample.pdf",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
