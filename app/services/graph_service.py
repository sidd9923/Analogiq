"""
GraphService
------------
Wraps the co-authorship social graph operations:

* Seeker profile retrieval (with DB caching)
* Graph expansion via Ray-parallel Semantic Scholar API calls
* Guide-finder: shortest-path BFS over NetworkX DiGraph
* Async job management (in-process for now; swap for Celery/Redis in prod)
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Optional

import networkx as nx
import ray
from semanticscholar import SemanticScholar

from app.core.exceptions import GraphError, SemanticScholarError
from app.core.models import GuidePath, JobStatus, SeekerProfile
from app.db.repositories import SeekerRepository, GraphRepository
from config.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ray remote: fetch a batch of co-author profiles
# ---------------------------------------------------------------------------
@ray.remote
def _fetch_coauthor_batch(author_ids: list[str], api_timeout: int = 30) -> list[str]:
    """
    For each author in the batch, fetch their papers and collect the IDs of
    *their* co-authors (second-degree expansion).  Returns a flat deduplicated
    list of author IDs.
    """
    sch = SemanticScholar(timeout=api_timeout)
    all_coauthors: set[str] = set()

    for author_id in author_ids:
        if not author_id:
            continue
        try:
            info = sch.get_author(author_id)
            for paper in info.get("papers", []):
                for a in paper.get("authors", []):
                    if a.get("authorId") and a["authorId"] != author_id:
                        all_coauthors.add(a["authorId"])
        except Exception as exc:
            logger.warning("Failed to fetch co-authors for %s: %s", author_id, exc)
        time.sleep(settings.SEMANTIC_SCHOLAR_RATE_DELAY)

    return list(all_coauthors)


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class GraphService:
    def __init__(self):
        self._sch = SemanticScholar(timeout=30)
        self._seeker_repo = SeekerRepository()
        self._graph_repo = GraphRepository()
        self._jobs: dict[str, JobStatus] = {}
        self._jobs_lock = threading.Lock()

        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True, num_cpus=settings.RAY_NUM_CPUS)

    # ------------------------------------------------------------------
    # Seeker info
    # ------------------------------------------------------------------

    def get_seeker_info(self, seeker_id: int) -> dict:
        # Cache hit
        cached = self._seeker_repo.get(seeker_id)
        if cached:
            return cached

        try:
            raw = self._sch.get_author(seeker_id)
        except Exception as exc:
            raise SemanticScholarError(f"Semantic Scholar API error: {exc}") from exc

        profile = SeekerProfile(
            seeker_id=seeker_id,
            name=raw["name"],
            position=None,
            paper_count=raw.get("paperCount", 0),
        )
        self._seeker_repo.save(profile)
        return {"seeker_id": seeker_id, "name": profile.name, "paper_count": profile.paper_count}

    # ------------------------------------------------------------------
    # Graph expansion (async)
    # ------------------------------------------------------------------

    def expand_async(self, seeker_id: int, circle_level: int = 1, batch_size: int = 10) -> str:
        job_id = str(uuid.uuid4())
        status = JobStatus(job_id=job_id, status="queued")

        with self._jobs_lock:
            self._jobs[job_id] = status

        t = threading.Thread(
            target=self._run_expansion,
            args=(job_id, seeker_id, circle_level, batch_size),
            daemon=True,
        )
        t.start()
        return job_id

    def _run_expansion(self, job_id: str, seeker_id: int, circle_level: int, batch_size: int):
        self._set_job_status(job_id, "running")
        try:
            graph = self._build_graph(seeker_id, circle_level, batch_size)
            self._graph_repo.save(seeker_id, graph)
            self._set_job_status(job_id, "done", result={
                "seeker_id": seeker_id,
                "circle_level": circle_level,
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
            })
        except Exception as exc:
            logger.exception("Graph expansion failed for seeker %d", seeker_id)
            self._set_job_status(job_id, "failed", error=str(exc))

    def _build_graph(self, seeker_id: int, circle_level: int, batch_size: int) -> nx.DiGraph:
        g = nx.DiGraph()
        g.add_node(seeker_id)

        # Circle 1: direct co-authors
        raw = self._sch.get_author(seeker_id)
        circle1_ids: list[str] = []
        for paper in raw.get("papers", []):
            for author in paper.get("authors", []):
                aid = author.get("authorId")
                if aid and aid != str(seeker_id):
                    circle1_ids.append(aid)
                    g.add_edge(seeker_id, int(aid))

        if circle_level < 2:
            return g

        # Circle 2: parallel Ray expansion
        unique_c1 = list(set(circle1_ids))
        batches = [unique_c1[i : i + batch_size] for i in range(0, len(unique_c1), batch_size)]
        futures = [_fetch_coauthor_batch.remote(b, settings.SEMANTIC_SCHOLAR_RATE_DELAY) for b in batches]
        c2_results = ray.get(futures)

        for author_id, c2_ids in zip(unique_c1, c2_results):
            for c2_id in c2_ids:
                try:
                    g.add_edge(int(author_id), int(c2_id))
                except (ValueError, TypeError):
                    pass

        return g

    # ------------------------------------------------------------------
    # Guide finder
    # ------------------------------------------------------------------

    def find_guides(
        self,
        seeker_id: int,
        guide_ids: list[int],
        max_hops: int = 3,
    ) -> list[dict]:
        graph = self._graph_repo.load(seeker_id)
        if graph is None:
            raise GraphError(
                f"No graph found for seeker {seeker_id}. "
                "Call POST /api/v1/graph/expand first."
            )

        results = []
        for guide_id in guide_ids:
            if not graph.has_node(guide_id):
                continue
            try:
                path = nx.shortest_path(graph, source=seeker_id, target=guide_id)
                length = len(path) - 1
                if length <= max_hops:
                    results.append(GuidePath(
                        guide_id=guide_id, path=path, path_length=length
                    ).__dict__)
            except nx.NetworkXNoPath:
                logger.debug("No path from %d to %d", seeker_id, guide_id)

        return results

    # ------------------------------------------------------------------
    # Job polling
    # ------------------------------------------------------------------

    def job_status(self, job_id: str) -> dict:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
        if job is None:
            return {"job_id": job_id, "status": "not_found"}
        return {
            "job_id": job.job_id,
            "status": job.status,
            **({"result": job.result} if job.result else {}),
            **({"error": job.error} if job.error else {}),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_job_status(self, job_id: str, status: str, result: Optional[dict] = None, error: Optional[str] = None):
        with self._jobs_lock:
            job = self._jobs[job_id]
            job.status = status
            job.result = result
            job.error = error
