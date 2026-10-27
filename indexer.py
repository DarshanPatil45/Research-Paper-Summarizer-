"""
Embedding and ChromaDB indexing / retrieval.

Each uploaded paper gets its own ChromaDB collection so that
evidence from one paper cannot leak into another paper's results.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from chunker import Chunk
from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL_NAME, TOP_K_RETRIEVAL

# ---------------------------------------------------------------------------
# Module-level singletons (lazy-initialised)
# ---------------------------------------------------------------------------
_embed_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.ClientAPI] = None


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embed_model


def _get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            is_persistent=True,
            persist_directory=CHROMA_PERSIST_DIR,
        ))
    return _chroma_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def collection_name_for(paper_id: str) -> str:
    """
    Deterministic collection name for a paper, safe for ChromaDB constraints
    (3-63 chars, starts/ends with alphanumeric, no consecutive periods).
    """
    h = hashlib.sha256(paper_id.encode()).hexdigest()[:16]
    return f"paper_{h}"


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a list of texts."""
    model = _get_embed_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


def index_chunks(paper_id: str, chunks: list[Chunk]) -> str:
    """
    Embed and store all chunks in a paper-specific ChromaDB collection.

    Returns the collection name.
    """
    client = _get_chroma_client()
    col_name = collection_name_for(paper_id)

    # Delete existing collection for this paper if it exists (re-upload)
    try:
        client.delete_collection(col_name)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "page_start": c.page_start,
            "page_end": c.page_end,
            "section": c.section,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]

    # ChromaDB add in batches (avoids huge payloads)
    batch = 100
    for i in range(0, len(texts), batch):
        collection.add(
            ids=ids[i:i + batch],
            documents=texts[i:i + batch],
            embeddings=embeddings[i:i + batch],
            metadatas=metadatas[i:i + batch],
        )

    return col_name


def retrieve(paper_id: str, query: str, top_k: int = TOP_K_RETRIEVAL) -> list[dict]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Returns a list of dicts with keys:
      text, page_start, page_end, section, chunk_index, distance
    """
    client = _get_chroma_client()
    col_name = collection_name_for(paper_id)

    try:
        collection = client.get_collection(col_name)
    except Exception:
        return []

    q_emb = embed_texts([query])
    results = collection.query(
        query_embeddings=q_emb,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text": doc,
            "page_start": meta["page_start"],
            "page_end": meta["page_end"],
            "section": meta.get("section", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "distance": dist,
        })

    return hits


def delete_paper_index(paper_id: str):
    """Remove the collection for a paper."""
    client = _get_chroma_client()
    col_name = collection_name_for(paper_id)
    try:
        client.delete_collection(col_name)
    except Exception:
        pass
