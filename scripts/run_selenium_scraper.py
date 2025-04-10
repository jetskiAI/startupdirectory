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

from app import create_app
from app.scrapers.selenium_yc_scraper import SeleniumYCScraper


def main():
    parser = argparse.ArgumentParser(description="Run YC Selenium scraper")
    parser.add_argument("--year", type=int, help="Filter startups by year (optional)")
    args = parser.parse_args()

    print(f"Starting YC Selenium scraper at {datetime.now()}")

    # Create and configure app
    app = create_app()

    # Run scraper in app context
    with app.app_context():
        print(f"Scraping YC startups for year: {args.year or 'all years'}")

        # Initialize and run the scraper
        scraper = SeleniumYCScraper()
        startups = scraper.fetch_startups(year=args.year)

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
