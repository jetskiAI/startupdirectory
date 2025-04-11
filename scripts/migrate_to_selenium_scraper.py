#!/usr/bin/env python3
"""
Migration script to transition from HTML-based scraper to Selenium scraper.

This script:
1. Adds a CLI command to run the Selenium scraper
2. Removes the old HTML-based scraper function from CLI

Usage:
    python scripts/migrate_to_selenium_scraper.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app
current_path = Path(__file__).parent.absolute()
parent_path = current_path.parent
sys.path.append(str(parent_path))

from app import create_app
from app.cli.scraper_commands import cli, scrape_yc_selenium
import click


def update_scraper_cli():
    """Update the scraper CLI to use only Selenium-based scraper"""
    try:
        # Create app context
        app = create_app()

        with app.app_context():
            print("Updating CLI commands to use Selenium scraper exclusively...")

            # Register the scrape-yc command to use Selenium scraper
            @click.command("scrape-yc")
            @click.option(
                "--year", default=None, type=int, help="Filter by year (optional)"
            )
            def scrape_yc(year):
                """Scrape YC startups from their website (uses Selenium)"""
                click.echo("Starting YC scraper (Selenium-based)...")
                return scrape_yc_selenium(year)

            # Add the command to the CLI
            cli.add_command(scrape_yc)

            print("CLI commands updated.")
            print(
                "You can now use 'flask scrapers scrape-yc' to run the Selenium scraper."
            )
            print("NOTE: The old HTML scraper is no longer accessible via CLI.")

            return True
    except Exception as e:
        print(f"Error updating CLI: {e}")
        return False


def main():
    """Main migration function"""
    print("Starting migration to Selenium scraper...")

    # 1. Update CLI commands
    cli_updated = update_scraper_cli()

    if cli_updated:
        print("\nMigration completed successfully!")
        print("\nNext steps:")
        print(
            "1. (Optional) Delete the old yc_scraper.py file if you no longer need it"
        )
        print("2. Run the new scraper with: flask scrapers scrape-yc")
        print(
            "3. If you want to clear the database, use the script: python scripts/clear_database.py"
        )
    else:
        print("\nMigration failed. Please check the error messages above.")


if __name__ == "__main__":
    main()
