"""
SearchService
-------------
Orchestrates the full analogical search pipeline:

  1. Encode query → sentence embedding (sentence-transformers)
  2. Approximate nearest-neighbour retrieval from FAISS index
  3. Re-rank candidates with the ensemble analogical score
  4. Return top-K results with latency

Indexing path (called by POST /api/v1/search/index):
  1. Encode document abstracts in batches via Ray
  2. Call FaissIndexManager.build()
  3. Fit StructuralSimilarity on the abstract corpus
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np
import ray
from sentence_transformers import SentenceTransformer

from app.core.faiss_index import FaissIndexManager
from app.core.similarity import (
    StructuralSimilarity,
    analogical_score,
    relational_similarity,
    semantic_similarity,
)
from config.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ray remote: encode a batch of texts
# ---------------------------------------------------------------------------
@ray.remote
def _encode_batch(texts: list[str], model_name: str) -> list[list[float]]:
    model = SentenceTransformer(model_name)
    return model.encode(texts, normalize_embeddings=True).tolist()


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class SearchService:
    def __init__(self):
        self._encoder = SentenceTransformer(settings.EMBEDDING_MODEL)
        self._faiss = FaissIndexManager()
        self._structural = StructuralSimilarity()
        self._corpus_abstracts: list[str] = []

        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True, num_cpus=settings.RAY_NUM_CPUS)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_documents(self, documents: list[dict]) -> int:
        """
        Encode and index a list of document dicts.

        Each doc must have: id, title, abstract, domain
        Optional keys: authors (list[str])
        """
        abstracts = [d["abstract"] for d in documents]
        metadata = [
            {
                "id": d["id"],
                "title": d["title"],
                "abstract": d["abstract"],
                "domain": d.get("domain", ""),
                "authors": d.get("authors", []),
            }
            for d in documents
        ]

        # Parallel encoding with Ray
        batch_size = settings.EMBEDDING_BATCH_SIZE
        batches = [abstracts[i : i + batch_size] for i in range(0, len(abstracts), batch_size)]
        futures = [_encode_batch.remote(b, settings.EMBEDDING_MODEL) for b in batches]
        encoded_batches = ray.get(futures)

        all_vectors = np.array(
            [vec for batch in encoded_batches for vec in batch], dtype=np.float32
        )

        self._faiss.build(all_vectors, metadata)
        self._structural.fit(abstracts)
        self._corpus_abstracts = abstracts

        logger.info("Indexed %d documents", len(documents))
        return len(documents)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def analogical_search(
        self,
        query: str,
        top_k: int = 10,
        domain_filter: Optional[str] = None,
    ) -> tuple[list[dict], float]:
        """
        Full analogical search pipeline.

        Returns (results, total_latency_ms).
        """
        t0 = time.perf_counter()

        # 1. Embed query
        query_vec = self._encoder.encode(query, normalize_embeddings=True)

        # 2. FAISS ANN retrieval (fetch 3x candidates for re-ranking)
        candidates, faiss_latency = self._faiss.search(
            query_vector=query_vec,
            top_k=top_k * 3,
            domain_filter=domain_filter,
        )

        # 3. Re-rank with ensemble analogical score
        reranked = []
        for c in candidates:
            sem = c["score"]  # already cosine from FAISS

            struct = 0.0
            if self._structural._fitted:
                struct = float(
                    self._structural.batch_score(query, [c["abstract"]])[0]
                )

            rel = relational_similarity(query, c["abstract"])
            final_score = analogical_score(sem, struct, rel)

            reranked.append({**c, "score": round(final_score, 4)})

        reranked.sort(key=lambda x: x["score"], reverse=True)
        results = reranked[:top_k]
        for i, r in enumerate(results, 1):
            r["rank"] = i

        total_latency = (time.perf_counter() - t0) * 1000
        logger.info(
            "Search completed: query_len=%d, results=%d, latency=%.1fms",
            len(query),
            len(results),
            total_latency,
        )
        return results, total_latency
