"""
SQLAlchemy ORM table definitions for Analogiq.

Tables
------
seekers       — cached Semantic Scholar author profiles
social_circles — co-author lists per seeker/level
guide_paths   — shortest-path results (seeker → guide)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Seeker(Base):
    __tablename__ = "seekers"

    seeker_id = Column(Integer, primary_key=True)  # Semantic Scholar author ID
    name = Column(String(256), nullable=False)
    position = Column(String(128))
    paper_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    circles = relationship("SocialCircle", back_populates="seeker", cascade="all, delete-orphan")
    guide_paths = relationship("GuidePath", back_populates="seeker", cascade="all, delete-orphan")


class SocialCircle(Base):
    __tablename__ = "social_circles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seeker_id = Column(Integer, ForeignKey("seekers.seeker_id"), nullable=False)
    level = Column(Integer, nullable=False)              # 1 or 2
    author_ids = Column(JSON, nullable=False)            # list of author ID strings
    created_at = Column(DateTime, default=datetime.utcnow)

    seeker = relationship("Seeker", back_populates="circles")


class GuidePath(Base):
    __tablename__ = "guide_paths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seeker_id = Column(Integer, ForeignKey("seekers.seeker_id"), nullable=False)
    guide_id = Column(Integer, nullable=False)
    path = Column(JSON, nullable=False)                  # list of node IDs
    path_length = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    seeker = relationship("Seeker", back_populates="guide_paths")
