"""
/api/v1/search  — analogical similarity search over indexed abstracts.
"""

from flask import Blueprint, jsonify, request

from app.services.search_service import SearchService
from app.core.exceptions import ValidationError, SearchError

search_bp = Blueprint("search", __name__)
_svc: SearchService | None = None


def get_service() -> SearchService:
    global _svc
    if _svc is None:
        _svc = SearchService()
    return _svc


# ---------------------------------------------------------------------------
# POST /api/v1/search/query
# ---------------------------------------------------------------------------
@search_bp.post("/query")
def query():
    """
    Retrieve the top-K analogically similar abstracts for a query problem.

    Request body (JSON):
        query       str   — problem description / research question (required)
        top_k       int   — number of results to return (default: 10, max: 50)
        domain      str   — optional source-domain filter (e.g. "biology")

    Response (JSON):
        results     list[{id, title, abstract, score, domain, authors}]
        latency_ms  float
    """
    body = request.get_json(silent=True) or {}

    query_text: str = body.get("query", "").strip()
    if not query_text:
        raise ValidationError("`query` field is required")

    top_k: int = min(int(body.get("top_k", 10)), 50)
    domain: str | None = body.get("domain")

    try:
        results, latency_ms = get_service().analogical_search(
            query=query_text,
            top_k=top_k,
            domain_filter=domain,
        )
    except Exception as exc:
        raise SearchError(str(exc)) from exc

    return jsonify({"results": results, "latency_ms": round(latency_ms, 2)})


# ---------------------------------------------------------------------------
# POST /api/v1/search/index   (admin / batch-load)
# ---------------------------------------------------------------------------
@search_bp.post("/index")
def index_documents():
    """
    Index a batch of documents into FAISS.

    Request body (JSON):
        documents  list[{id, title, abstract, domain, authors}]

    Response (JSON):
        indexed    int  — number of documents successfully indexed
    """
    body = request.get_json(silent=True) or {}
    docs = body.get("documents", [])

    if not isinstance(docs, list) or not docs:
        raise ValidationError("`documents` must be a non-empty list")

    count = get_service().index_documents(docs)
    return jsonify({"indexed": count}), 201


# ---------------------------------------------------------------------------
# Error handlers (scoped to this blueprint)
# ---------------------------------------------------------------------------
@search_bp.errorhandler(ValidationError)
def handle_validation(err):
    return jsonify({"error": str(err)}), 400


@search_bp.errorhandler(SearchError)
def handle_search(err):
    return jsonify({"error": str(err)}), 500
