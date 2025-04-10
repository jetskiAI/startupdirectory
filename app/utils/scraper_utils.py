from datetime import datetime, timedelta
from sqlalchemy import desc
import logging

from app.models.scraper_run import ScraperRun

# Configure logging
logger = logging.getLogger(__name__)


def should_run_full_update(source="YC", interval_months=3, db=None):
    """
    Check if a full update should be run based on last successful run

    Args:
        source (str): Source identifier (YC, Neo, etc.)
        interval_months (int): Months between full updates
        db: SQLAlchemy database instance

    Returns:
        bool: True if update should run, False otherwise
    """
    if db is None:
        logger.error("Database instance required to check update status")
        return True  # Default to running if we can't check

    try:
        # Find the last successful run
        last_run = (
            db.session.query(ScraperRun)
            .filter_by(source=source, status="success")
            .order_by(desc(ScraperRun.end_time))
            .first()
        )

        if not last_run:
            logger.info(f"No previous successful runs found for {source}")
            return True

        # Calculate time since last update
        now = datetime.utcnow()
        months_since_update = (now - last_run.end_time).days / 30

        if months_since_update >= interval_months:
            logger.info(
                f"Last {source} update was {months_since_update:.1f} months ago. Running update."
            )
            return True
        else:
            logger.info(
                f"Last {source} update was only {months_since_update:.1f} months ago. Skipping."
            )
            return False

    except Exception as e:
        logger.error(f"Error checking update status: {e}")
        return True  # Default to running on error


def create_scraper_run(source, db):
    """
    Create and return a new scraper run record

    Args:
        source (str): Source identifier (YC, Neo, etc.)
        db: SQLAlchemy database instance

    Returns:
        ScraperRun: The created run record
    """
    run = ScraperRun(source=source)
    db.session.add(run)
    db.session.commit()
    return run


def complete_scraper_run(run_id, status, stats, error_message=None, db=None):
    """
    Update a scraper run with completion details

    Args:
        run_id (int): ID of the run to update
        status (str): Final status (success/failed)
        stats (dict): Statistics dictionary with counts
        error_message (str, optional): Error details if failed
        db: SQLAlchemy database instance

    Returns:
        ScraperRun: The updated run record
    """
    if db is None:
        logger.error("Database instance required to update run status")
        return None

    try:
        run = db.session.query(ScraperRun).get(run_id)
        if not run:
            logger.error(f"Run with ID {run_id} not found")
            return None

        run.end_time = datetime.utcnow()
        run.status = status
        run.error_message = error_message

        # Update statistics
        run.startups_added = stats.get("added", 0)
        run.startups_updated = stats.get("updated", 0)
        run.startups_unchanged = stats.get("unchanged", 0)
        run.total_processed = stats.get("total", 0)

        db.session.commit()
        return run

    except Exception as e:
        logger.error(f"Error updating run status: {e}")
        return None
