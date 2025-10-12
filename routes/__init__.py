"""
Routes Package - Initialize all route blueprints
"""

from .catalog_routes import catalog_bp
from .borrowing_routes import borrowing_bp
from .search_routes import search_bp
from .api_routes import api_bp
from .user_routes import user_bp  # Import user blueprint - A2

def register_blueprints(app):
    """Register all route blueprints with the Flask app."""
    app.register_blueprint(catalog_bp)
    app.register_blueprint(borrowing_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(user_bp)  # Register user blueprint - A2
