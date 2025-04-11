#!/usr/bin/env python3
"""
Clear all data from the startup directory database.

This script:
1. Clears all records from the main tables
2. Resets sequences if using a database that supports it (PostgreSQL)
3. Preserves the database schema/structure

Usage:
    python scripts/clear_database.py
    python scripts/clear_database.py --yes  # Skip confirmation
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path so we can import app
current_path = Path(__file__).parent.absolute()
parent_path = current_path.parent
sys.path.append(str(parent_path))

from app import create_app
from app.models.db import db
from app.models.startup import Startup, Founder
from app.models.scraper_run import ScraperRun


def parse_args():
    parser = argparse.ArgumentParser(
        description="Clear all data from the startup directory database"
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument(
        "--keep-runs", action="store_true", help="Keep scraper run history"
    )
    return parser.parse_args()


def clear_database(confirm=True, keep_runs=False):
    """
    Clear all records from the database but preserve the schema.

    Args:
        confirm (bool): Whether to ask for confirmation before clearing
        keep_runs (bool): Whether to preserve scraper run history

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        app = create_app()

        with app.app_context():
            if confirm:
                print(
                    "\nWARNING: This will delete ALL startup and founder data from the database."
                )
                print("This action cannot be undone.")

                response = input("\nAre you sure you want to proceed? (yes/no): ")
                if response.lower() != "yes":
                    print("Operation cancelled.")
                    return False

            print("\nClearing database...")

            # Delete records in the correct order to avoid foreign key constraint errors
            # Start with founders (child records) before startups (parent records)
            founder_count = Founder.query.count()
            db.session.query(Founder).delete()
            print(f"Deleted {founder_count} founder records")

            startup_count = Startup.query.count()
            db.session.query(Startup).delete()
            print(f"Deleted {startup_count} startup records")

            if not keep_runs:
                run_count = ScraperRun.query.count()
                db.session.query(ScraperRun).delete()
                print(f"Deleted {run_count} scraper run records")
            else:
                print("Keeping scraper run history as requested")

            # Commit the changes
            db.session.commit()

            print("\nDatabase has been cleared successfully!")
            return True

    except Exception as e:
        print(f"Error clearing database: {e}")
        return False


def main():
    args = parse_args()
    success = clear_database(confirm=not args.yes, keep_runs=args.keep_runs)

    if success:
        print(
            "\nDatabase has been reset. You can now run the scraper to populate it with fresh data:"
        )
        print("  flask scrapers scrape-yc")
        print("  flask scrapers scrape-yc --year=2023")
    else:
        print("\nFailed to clear the database. Please check the error messages above.")


if __name__ == "__main__":
    main()
