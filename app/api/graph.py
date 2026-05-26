"""
/api/v1/graph  — social-proximity graph construction and guide-finder queries.
"""

from flask import Blueprint, jsonify, request

from app.services.graph_service import GraphService
from app.core.exceptions import ValidationError, GraphError

graph_bp = Blueprint("graph", __name__)
_svc: GraphService | None = None


def get_service() -> GraphService:
    global _svc
    if _svc is None:
        _svc = GraphService()
    return _svc


# ---------------------------------------------------------------------------
# GET /api/v1/graph/seeker/<seeker_id>
# ---------------------------------------------------------------------------
@graph_bp.get("/seeker/<int:seeker_id>")
def get_seeker(seeker_id: int):
    """
    Return cached seeker profile (name, paper count) for a Semantic Scholar
    author ID.  Fetches from the external API if not already stored.

    Response (JSON):
        seeker_id   int
        name        str
        paper_count int
    """
    try:
        info = get_service().get_seeker_info(seeker_id)
    except Exception as exc:
        raise GraphError(str(exc)) from exc

    return jsonify(info)


# ---------------------------------------------------------------------------
# POST /api/v1/graph/expand
# ---------------------------------------------------------------------------
@graph_bp.post("/expand")
def expand_graph():
    """
    Expand the co-authorship graph for a seeker up to *circle_level* hops.
    Heavy work is dispatched to Ray workers asynchronously; returns a job_id
    that can be polled via GET /api/v1/graph/job/<job_id>.

    Request body (JSON):
        seeker_id     int   — Semantic Scholar author ID (required)
        circle_level  int   — depth to expand: 1 or 2 (default: 1)
        batch_size    int   — authors per Ray task (default: 10)
    """
    body = request.get_json(silent=True) or {}

    seeker_id = body.get("seeker_id")
    if seeker_id is None:
        raise ValidationError("`seeker_id` is required")

    circle_level: int = int(body.get("circle_level", 1))
    if circle_level not in (1, 2):
        raise ValidationError("`circle_level` must be 1 or 2")

    batch_size: int = int(body.get("batch_size", 10))

    job_id = get_service().expand_async(
        seeker_id=int(seeker_id),
        circle_level=circle_level,
        batch_size=batch_size,
    )
    return jsonify({"job_id": job_id, "status": "queued"}), 202


# ---------------------------------------------------------------------------
# POST /api/v1/graph/guides
# ---------------------------------------------------------------------------
@graph_bp.post("/guides")
def find_guides():
    """
    Find the shortest path(s) from a seeker to one or more guide authors in
    the pre-built social graph.

    Request body (JSON):
        seeker_id   int        — Semantic Scholar author ID
        guide_ids   list[int]  — author IDs to route to
        max_hops    int        — maximum path length to consider (default: 3)

    Response (JSON):
        guides  list[{guide_id, path, path_length}]
    """
    body = request.get_json(silent=True) or {}

    seeker_id = body.get("seeker_id")
    guide_ids = body.get("guide_ids", [])

    if seeker_id is None or not guide_ids:
        raise ValidationError("`seeker_id` and non-empty `guide_ids` are required")

    max_hops: int = int(body.get("max_hops", 3))

    try:
        results = get_service().find_guides(
            seeker_id=int(seeker_id),
            guide_ids=[int(g) for g in guide_ids],
            max_hops=max_hops,
        )
    except Exception as exc:
        raise GraphError(str(exc)) from exc

    return jsonify({"guides": results})


# ---------------------------------------------------------------------------
# GET /api/v1/graph/job/<job_id>
# ---------------------------------------------------------------------------
@graph_bp.get("/job/<job_id>")
def poll_job(job_id: str):
    """
    Poll the status of an async graph-expansion job.

    Response (JSON):
        job_id    str
        status    str   — "queued" | "running" | "done" | "failed"
        result    dict  — present when status == "done"
    """
    status = get_service().job_status(job_id)
    return jsonify(status)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@graph_bp.errorhandler(ValidationError)
def handle_validation(err):
    return jsonify({"error": str(err)}), 400


@graph_bp.errorhandler(GraphError)
def handle_graph(err):
    return jsonify({"error": str(err)}), 500
