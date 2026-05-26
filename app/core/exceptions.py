"""Custom exception types for Analogiq."""


class AnalogiQError(Exception):
    """Base class for all Analogiq application errors."""


class ValidationError(AnalogiQError):
    """Raised when request input fails validation."""


class SearchError(AnalogiQError):
    """Raised when the FAISS search pipeline fails."""


class GraphError(AnalogiQError):
    """Raised when a graph operation (expansion, BFS, shortest-path) fails."""


class IndexNotReadyError(AnalogiQError):
    """Raised when a search is attempted before the FAISS index is loaded."""


class SemanticScholarError(AnalogiQError):
    """Raised when the Semantic Scholar API returns an error or rate-limits us."""
