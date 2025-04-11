#!/usr/bin/env python3
"""
Startup data collection script for scheduled runs via GitHub Actions.
This script collects data from various startup accelerators and
stores it in the project database.

python scripts/collect_data.py --source=yc
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow imports from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import app and models after setting up path
from app import create_app
from app.models.db import db
from app.models.startup import Startup, Founder
from app.models.scraper_run import ScraperRun
from app.scrapers.selenium_yc_scraper import SeleniumYCScraper
from app.utils.scraper_utils import should_run_full_update

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def setup_argparse():
    """Set up command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Collect startup data from accelerators"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["yc", "neo", "techstars", "all"],
        help="Source to collect data from (yc, neo, techstars, or all)",
    )
    parser.add_argument("--year", type=int, help="Year to filter by (optional)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force data collection even if recent update exists",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if update is needed, don't perform collection",
    )
    return parser.parse_args()


def save_startup_data(startup_data):
    """Save startup data to the database"""
    # Extract founders info
    founders_data = startup_data.pop("founders", [])

    # Check if startup already exists
    existing_startup = Startup.query.filter_by(
        name=startup_data["name"], year_founded=startup_data["year_founded"]
    ).first()

    if existing_startup:
        logger.info(f"Updating existing startup: {startup_data['name']}")
        # Update existing startup
        for key, value in startup_data.items():
            setattr(existing_startup, key, value)
        startup = existing_startup
    else:
        logger.info(f"Creating new startup: {startup_data['name']}")
        # Create new startup
        startup = Startup(**startup_data)
        db.session.add(startup)

    # Flush to get startup ID
    db.session.flush()

    # Process founders
    for founder_data in founders_data:
        # Check if founder already exists
        existing_founder = Founder.query.filter_by(
            name=founder_data["name"], startup_id=startup.id
        ).first()

        if existing_founder:
            # Update existing founder
            for key, value in founder_data.items():
                setattr(existing_founder, key, value)
        else:
            # Create new founder
            founder = Founder(**founder_data)
            founder.startup_id = startup.id
            db.session.add(founder)

    db.session.commit()
    return startup


def collect_yc_data(year=None, force=False):
    """Collect data from Y Combinator using Selenium scraper"""
    # Check if we should run the update
    if not force and not should_run_full_update(source="YC", db=db):
        logger.info("Skipping YC update - last run was less than 3 months ago")
        return 0

    logger.info(f"Collecting YC data for {'all years' if year is None else year}")
    scraper = SeleniumYCScraper()

    # Fetch startups - tracking is handled inside the scraper
    startups = scraper.fetch_startups(year, track_run=True)

    logger.info(f"Processed {len(startups)} YC startups")
    logger.info(
        f"Added: {scraper.stats['added']}, Updated: {scraper.stats['updated']}, Unchanged: {scraper.stats['unchanged']}"
    )

    return len(startups)


def collect_neo_data(year=None, force=False):
    """Collect data from Neo (placeholder)"""
    # Check if we should run the update
    if not force and not should_run_full_update(source="Neo", db=db):
        logger.info("Skipping Neo update - last run was less than 3 months ago")
        return 0

    # This would use a Neo scraper implementation
    logger.info(f"Neo scraper not yet implemented")
    return 0


def collect_techstars_data(year=None, force=False):
    """Collect data from TechStars (placeholder)"""
    # Check if we should run the update
    if not force and not should_run_full_update(source="TechStars", db=db):
        logger.info("Skipping TechStars update - last run was less than 3 months ago")
        return 0

    # This would use a TechStars scraper implementation
    logger.info(f"TechStars scraper not yet implemented")
    return 0


def check_update_status():
    """Check if updates are needed for each source"""
    results = {}
    sources = ["YC", "Neo", "TechStars"]

    for source in sources:
        needs_update = should_run_full_update(source=source, db=db)

        # Find last successful run
        last_run = (
            db.session.query(ScraperRun)
            .filter_by(source=source, status="success")
            .order_by(ScraperRun.end_time.desc())
            .first()
        )

        # Calculate days since last update
        days_since = None
        if last_run and last_run.end_time:
            days_since = (datetime.utcnow() - last_run.end_time).days

        results[source] = {
            "needs_update": needs_update,
            "last_update": last_run.end_time if last_run else None,
            "days_since_update": days_since,
        }

    return results


def main():
    """Main entry point for the data collection script"""
    args = setup_argparse()

    # Create and configure the Flask app
    app = create_app()

    # Database operations happen here:
    # Use app context for database operations
    with app.app_context():
        # If only checking status, print and exit
        if args.check_only:
            status = check_update_status()
            logger.info("Update status for data sources:")
            for source, info in status.items():
                days = info["days_since_update"] or "never"
                needs_update = "NEEDED" if info["needs_update"] else "not needed"
                logger.info(
                    f"  {source}: Last updated {days} days ago. Update {needs_update}"
                )
            return

        total_startups = 0

        if args.source == "yc" or args.source == "all":
            total_startups += collect_yc_data(args.year, args.force)

        if args.source == "neo" or args.source == "all":
            total_startups += collect_neo_data(args.year, args.force)

        if args.source == "techstars" or args.source == "all":
            total_startups += collect_techstars_data(args.year, args.force)

        logger.info(f"Data collection completed. Total startups: {total_startups}")


if __name__ == "__main__":
    main()
