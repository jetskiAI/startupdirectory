#!/usr/bin/env python3
"""
Script to trigger remote scraping via API endpoints.
This is used by GitHub Actions to request scraping operations
from a deployed API server.
"""

import os
import sys
import argparse
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API endpoints
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")
API_KEY = os.getenv("API_KEY")


def setup_argparse():
    """Set up command line argument parsing"""
    parser = argparse.ArgumentParser(description="Trigger remote scraping via API")
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["yc", "neo", "techstars", "all"],
        help="Source to collect data from (yc, neo, techstars, or all)",
    )
    parser.add_argument("--year", type=int, help="Year to filter by (optional)")
    return parser.parse_args()


def trigger_scrape(source, year=None):
    """Trigger remote scraping via API call"""
    url = f"{API_BASE_URL}/admin/scrape"

    # Prepare headers and parameters
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    params = {"source": source}

    if year:
        params["year"] = year

    try:
        logger.info(
            f"Triggering scrape for {source}" + (f" year {year}" if year else "")
        )
        response = requests.post(url, headers=headers, json=params)
        response.raise_for_status()

        result = response.json()
        logger.info(f"Scrape triggered successfully: {result}")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering scrape: {e}")
        if hasattr(e, "response") and e.response:
            logger.error(f"Response: {e.response.text}")
        return None


def main():
    """Main entry point for the script"""
    args = setup_argparse()

    if not API_KEY:
        logger.error("API_KEY environment variable not set")
        sys.exit(1)

    if args.source == "all":
        # Trigger all scrapers separately
        trigger_scrape("yc", args.year)
        trigger_scrape("neo", args.year)
        trigger_scrape("techstars", args.year)
    else:
        # Trigger specific scraper
        trigger_scrape(args.source, args.year)


if __name__ == "__main__":
    main()
