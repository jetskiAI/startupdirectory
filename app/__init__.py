import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
from config import Config

from app.api.startup_routes import startup_bp
from app.api.admin_routes import admin_bp
from app.models.db import db, init_db

# from app.cli.scraper_commands import cli as scraper_cli

load_dotenv()

migrate = Migrate()


def create_app(config_class=Config):
    """It configures the database connection, sets up routes (URLs), and other settings"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    # Register CLI commands
    from app.cli.scraper_commands import register_commands

    register_commands(app)

    # Register blueprints
    app.register_blueprint(startup_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    @app.route("/")
    def health_check():
        return {"status": "healthy", "message": "Startup Directory API is running"}

    return app
