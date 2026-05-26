from flask import Flask


def register_blueprints(app: Flask) -> None:
    from app.api.search import search_bp
    from app.api.graph import graph_bp
    from app.api.health import health_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(search_bp, url_prefix="/api/v1/search")
    app.register_blueprint(graph_bp, url_prefix="/api/v1/graph")
