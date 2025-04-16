from flask_sqlalchemy import SQLAlchemy
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()


def init_db(app):
    """Initialize the database"""
    try:
        # Import models here to ensure they are registered with SQLAlchemy
        from app.models.startup import Startup, Founder
        from app.models.scraper_run import ScraperRun

        # Create all tables
        with app.app_context():
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

    return db
