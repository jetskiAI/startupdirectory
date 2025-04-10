import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv

from app.models.db import init_db
from app.api.startup_routes import startup_bp
from app.api.admin_routes import admin_bp

load_dotenv()

migrate = Migrate()


def create_app(config=None):
    '''It configures the database connection, sets up routes (URLs), and other settings'''
    app = Flask(__name__)

    # Configure app
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Initialize extensions
    db = init_db(app)
    migrate.init_app(app, db)
    CORS(app)

    # Register blueprints
    app.register_blueprint(startup_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    @app.route("/")
    def health_check():
        return {"status": "healthy", "message": "Startup Directory API is running"}

    return app
