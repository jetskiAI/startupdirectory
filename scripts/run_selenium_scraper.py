#!/usr/bin/env python3
"""
Script to run the Selenium-based YC scraper with proper Flask context
"""

import os
import sys
import argparse
from datetime import datetime

# Add the parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.scrapers.selenium_yc_scraper import SeleniumYCScraper
from app.models.startup import Startup, Founder


def main():
    parser = argparse.ArgumentParser(description="Run YC Selenium scraper")
    parser.add_argument("--year", type=int, help="Filter startups by year (optional)")
    parser.add_argument(
        "--limit", type=int, help="Maximum number of startups to process (optional)"
    )
    args = parser.parse_args()

    print(f"Starting YC Selenium scraper at {datetime.now()}")

    # Create and configure app
    app = create_app()

    # Run scraper in app context
    with app.app_context():
        print(
            f"Scraping YC startups for year: {args.year or 'all years'}, limit: {args.limit or 'none'}"
        )

        # Initialize and run the scraper
        scraper = SeleniumYCScraper()
        startups = scraper.fetch_startups(year=args.year, limit=args.limit)

        # Process and save each startup
        for startup_data in startups:
            try:
                # Extract founders info
                founders_data = startup_data.pop("founders", [])

                # Check if startup exists
                existing_startup = Startup.query.filter_by(
                    name=startup_data["name"], batch=startup_data.get("batch")
                ).first()

                if existing_startup:
                    print(f"Updating existing startup: {startup_data['name']}")
                    # Update existing startup
                    for key, value in startup_data.items():
                        setattr(existing_startup, key, value)
                    startup = existing_startup
                else:
                    print(f"Creating new startup: {startup_data['name']}")
                    # Create new startup
                    startup = Startup(**startup_data)
                    db.session.add(startup)

                # Need to flush to get the startup ID
                db.session.flush()

                # Process founders
                for founder_data in founders_data:
                    # Check if founder exists
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

                # Commit each startup individually
                db.session.commit()
                print(f"Successfully saved startup: {startup_data['name']}")

            except Exception as e:
                print(
                    f"Error saving startup {startup_data.get('name', 'unknown')}: {e}"
                )
                db.session.rollback()
                continue

        # Print statistics
        print("\nSCRAPER RESULTS:")
        print("===============")
        print(f"Total companies processed: {scraper.stats['total']}")
        print(f"New companies added: {scraper.stats['added']}")
        print(f"Existing companies updated: {scraper.stats['updated']}")
        print(f"Unchanged companies: {scraper.stats['unchanged']}")

        if scraper.stats["total"] == 0:
            print(
                "\nWARNING: No startups were found or processed. Check the logs for errors."
            )
        else:
            print(f"\nSuccessfully processed {scraper.stats['total']} YC startups")

    print(f"Completed at {datetime.now()}")


if __name__ == "__main__":
    main()
