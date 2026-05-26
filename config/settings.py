"""
Configuration management for Analogiq.

Priority (highest → lowest):
  1. Environment variables
  2. .env file (loaded by python-dotenv)
  3. Defaults defined here

Usage
-----
from config.settings import settings
print(settings.EMBEDDING_MODEL)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    # ------------------------------------------------------------------ Flask
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    TESTING: bool = False
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # ------------------------------------------------------------------ Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'analogiq.db'}"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    # ------------------------------------------------------------------ FAISS
    FAISS_INDEX_PATH: Path = Path(
        os.getenv("FAISS_INDEX_PATH", str(BASE_DIR / "data" / "faiss.index"))
    )
    FAISS_IVF_THRESHOLD: int = int(os.getenv("FAISS_IVF_THRESHOLD", "100000"))
    FAISS_NPROBE: int = int(os.getenv("FAISS_NPROBE", "32"))

    # ------------------------------------------------------------------ Embeddings
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "allenai-specter"  # domain-adapted for scientific papers
    )
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))

    # ------------------------------------------------------------------ Similarity weights
    ANALOGY_WEIGHT_SEMANTIC: float = float(os.getenv("ANALOGY_WEIGHT_SEMANTIC", "0.60"))
    ANALOGY_WEIGHT_STRUCTURAL: float = float(os.getenv("ANALOGY_WEIGHT_STRUCTURAL", "0.25"))
    ANALOGY_WEIGHT_RELATIONAL: float = float(os.getenv("ANALOGY_WEIGHT_RELATIONAL", "0.15"))

    # ------------------------------------------------------------------ Ray
    RAY_NUM_CPUS: int = int(os.getenv("RAY_NUM_CPUS", "4"))

    # ------------------------------------------------------------------ Semantic Scholar
    SEMANTIC_SCHOLAR_RATE_DELAY: float = float(
        os.getenv("SEMANTIC_SCHOLAR_RATE_DELAY", "5.0")
    )

    # ------------------------------------------------------------------ Graph store
    GRAPH_STORE_PATH: Path = Path(
        os.getenv("GRAPH_STORE_PATH", str(BASE_DIR / "data" / "graphs"))
    )


settings = Settings()


# ---------------------------------------------------------------------------
# Flask config objects (used by create_app)
# ---------------------------------------------------------------------------

class _BaseConfig:
    SECRET_KEY = settings.SECRET_KEY
    SQLALCHEMY_DATABASE_URI = settings.DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = settings.CORS_ORIGINS


class DevelopmentConfig(_BaseConfig):
    DEBUG = True
    DB_ECHO = True


class ProductionConfig(_BaseConfig):
    DEBUG = False
    DB_ECHO = False


class TestingConfig(_BaseConfig):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"


_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(env: str = "development"):
    return _CONFIG_MAP.get(env, DevelopmentConfig)
