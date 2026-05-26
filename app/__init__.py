"""
Analogiq — Cross-domain scientific idea retrieval engine.
Application factory.
"""

from flask import Flask
from flask_cors import CORS

from app.api import register_blueprints
from app.db.session import init_db
from config.settings import get_config


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    cfg = get_config(env)
    app.config.from_object(cfg)

    CORS(app, resources={r"/api/*": {"origins": cfg.CORS_ORIGINS}})

    init_db(app)
    register_blueprints(app)

    return app
