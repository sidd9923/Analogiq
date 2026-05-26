"""
Core domain models for Analogiq.
Kept as plain dataclasses so they're serialisable without ORM coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    domain: str
    authors: list[str] = field(default_factory=list)


@dataclass
class SeekerProfile:
    seeker_id: int
    name: str
    position: Optional[str]
    paper_count: int
    papers: list[Paper] = field(default_factory=list)


@dataclass
class SearchResult:
    paper: Paper
    score: float          # cosine similarity in [0, 1]
    rank: int


@dataclass
class GuidePath:
    guide_id: int
    path: list[int]       # node IDs from seeker → guide
    path_length: int


@dataclass
class JobStatus:
    job_id: str
    status: str           # queued | running | done | failed
    result: Optional[dict] = None
    error: Optional[str] = None
