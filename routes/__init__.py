"""
Routes Package - Initialize all route blueprints
"""
def register_blueprints(app):
    """Register all route blueprints with the Flask app."""
    # Import inside this function so missing optional modules do not break startup
    from .catalog_routes import catalog_bp
    from .borrowing_routes import borrowing_bp
    from .search_routes import search_bp
    from .api_routes import api_bp

    app.register_blueprint(catalog_bp)
    app.register_blueprint(borrowing_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(api_bp)

    # Optional for A2. If user_routes.py is not present yet, skip it.
    try:
        from .user_routes import user_bp
        app.register_blueprint(user_bp)
    except Exception:
        pass