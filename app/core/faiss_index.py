"""
FAISS index management for analogical search.

Responsibilities
----------------
* Build or load a flat L2 / cosine FAISS index over sentence embeddings.
* Persist the index + metadata to disk so it survives restarts.
* Provide a thread-safe `search()` method used by SearchService.

The actual data (abstracts, embeddings) is NOT committed to version control.
Index files are stored at the path configured by settings.FAISS_INDEX_PATH.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from app.core.exceptions import IndexNotReadyError
from config.settings import settings

logger = logging.getLogger(__name__)


class FaissIndexManager:
    """
    Manages a FAISS IndexFlatIP (inner-product / cosine) index.

    Usage
    -----
    mgr = FaissIndexManager()
    mgr.build(vectors, metadata)   # one-time indexing
    results = mgr.search(query_vec, top_k=10)
    """

    def __init__(self, index_path: Optional[Path] = None):
        self._index_path = Path(index_path or settings.FAISS_INDEX_PATH)
        self._meta_path = self._index_path.with_suffix(".meta.json")
        self._index: Optional[faiss.Index] = None
        self._metadata: list[dict] = []
        self._lock = threading.RLock()
        self._loaded = False

        if self._index_path.exists() and self._meta_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, vectors: np.ndarray, metadata: list[dict]) -> None:
        """
        Build (or rebuild) the FAISS index from a matrix of L2-normalised
        sentence embeddings and a parallel list of metadata dicts.

        Parameters
        ----------
        vectors  : float32 numpy array of shape (N, D)
        metadata : list of dicts, len == N, each with at least {id, title, domain}
        """
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)

        # L2-normalise so inner product == cosine similarity
        faiss.normalize_L2(vectors)

        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)

        # Optionally wrap with an IVF for datasets > 100k vectors
        if len(vectors) > settings.FAISS_IVF_THRESHOLD:
            nlist = min(int(len(vectors) ** 0.5), 4096)
            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
            index.train(vectors)
            index.nprobe = settings.FAISS_NPROBE

        index.add(vectors)

        with self._lock:
            self._index = index
            self._metadata = metadata
            self._loaded = True

        self._save()
        logger.info("FAISS index built: %d vectors, dim=%d", len(vectors), dim)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        domain_filter: Optional[str] = None,
    ) -> tuple[list[dict], float]:
        """
        Search the index for the *top_k* most analogically similar documents.

        Parameters
        ----------
        query_vector  : float32 array of shape (D,) or (1, D)
        top_k         : number of results (before optional domain filtering)
        domain_filter : if set, return only results matching this domain string

        Returns
        -------
        (results, latency_ms)
            results is a list of dicts: {id, title, abstract, domain, authors, score, rank}
        """
        if not self._loaded or self._index is None:
            raise IndexNotReadyError("FAISS index is not loaded. Run /api/v1/search/index first.")

        qv = np.array(query_vector, dtype=np.float32)
        if qv.ndim == 1:
            qv = qv.reshape(1, -1)
        faiss.normalize_L2(qv)

        # Fetch extra candidates if filtering by domain
        fetch_k = top_k * 5 if domain_filter else top_k

        with self._lock:
            t0 = time.perf_counter()
            scores, indices = self._index.search(qv, fetch_k)
            latency_ms = (time.perf_counter() - t0) * 1000

        results = []
        rank = 1
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = self._metadata[idx]
            if domain_filter and meta.get("domain", "").lower() != domain_filter.lower():
                continue
            results.append({**meta, "score": float(score), "rank": rank})
            rank += 1
            if rank > top_k:
                break

        return results, latency_ms

    @property
    def size(self) -> int:
        return self._index.ntotal if self._index else 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path))
        with open(self._meta_path, "w") as f:
            json.dump(self._metadata, f)
        logger.info("FAISS index persisted to %s", self._index_path)

    def _load(self) -> None:
        try:
            self._index = faiss.read_index(str(self._index_path))
            with open(self._meta_path) as f:
                self._metadata = json.load(f)
            self._loaded = True
            logger.info("FAISS index loaded from %s (%d vectors)", self._index_path, self._index.ntotal)
        except Exception:
            logger.exception("Failed to load FAISS index from disk")
