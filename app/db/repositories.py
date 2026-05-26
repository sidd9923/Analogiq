"""
Repository layer — thin wrappers around SQLAlchemy sessions.

Pattern: one repository class per aggregate root.
Services only talk to repositories; never to SQLAlchemy directly.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional

import networkx as nx

from app.core.models import SeekerProfile
from app.db.models import GuidePath as GuidePath_ORM
from app.db.models import Seeker as Seeker_ORM
from app.db.session import get_session
from config.settings import settings


class SeekerRepository:
    def get(self, seeker_id: int) -> Optional[dict]:
        with get_session() as s:
            row = s.get(Seeker_ORM, seeker_id)
            if row is None:
                return None
            return {"seeker_id": row.seeker_id, "name": row.name, "paper_count": row.paper_count}

    def save(self, profile: SeekerProfile) -> None:
        with get_session() as s:
            existing = s.get(Seeker_ORM, profile.seeker_id)
            if existing:
                existing.name = profile.name
                existing.paper_count = profile.paper_count
            else:
                s.add(Seeker_ORM(
                    seeker_id=profile.seeker_id,
                    name=profile.name,
                    paper_count=profile.paper_count,
                ))


class GraphRepository:
    """
    Persist NetworkX graph objects as pickled files in the graph-store dir.
    Each seeker gets one file: <graph_store>/<seeker_id>.pkl

    A production system would use Neo4j or a similar graph DB; the pickle
    approach keeps local dev simple while being easy to swap out.
    """

    def __init__(self):
        self._store = Path(settings.GRAPH_STORE_PATH)
        self._store.mkdir(parents=True, exist_ok=True)

    def save(self, seeker_id: int, graph: nx.DiGraph) -> None:
        path = self._store / f"{seeker_id}.pkl"
        with open(path, "wb") as f:
            pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load(self, seeker_id: int) -> Optional[nx.DiGraph]:
        path = self._store / f"{seeker_id}.pkl"
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return pickle.load(f)
