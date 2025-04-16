import click
from flask.cli import with_appcontext
from app.scrapers.selenium_yc_scraper import SeleniumYCScraper
from app.models.db import db
from app.models.scraper_run import ScraperRun
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@click.group()
def scraper():
    """Commands for managing the YC scraper"""
    pass


@scraper.command()
@click.option("--year", type=int, help="Filter startups by year")
@click.option(
    "--headless/--no-headless", default=True, help="Run browser in headless mode"
)
@click.option("--wait-time", type=int, default=10, help="Wait time for page loading")
@with_appcontext
def run(year, headless, wait_time):
    """Run the YC scraper"""
    try:
        logger.info(
            f"Starting scraper with year={year}, headless={headless}, wait_time={wait_time}"
        )
        scraper = SeleniumYCScraper()
        startups = scraper.fetch_startups(
            year=year, headless=headless, wait_time=wait_time
        )
        logger.info(f"Successfully scraped {len(startups)} startups")
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        raise click.ClickException(str(e))


@scraper.command()
@click.option("--days", type=int, default=7, help="Number of days to look back")
@with_appcontext
def check_runs(days):
    """Check recent scraper runs"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        runs = ScraperRun.query.filter(ScraperRun.created_at >= cutoff_date).all()

        if not runs:
            click.echo(f"No scraper runs found in the last {days} days")
            return

        click.echo(f"\nRecent Scraper Runs (last {days} days):")
        click.echo("=" * 80)

        for run in runs:
            status_color = "green" if run.status == "success" else "red"
            click.echo(f"\nRun #{run.id}")
            click.echo(f"Status: {click.style(run.status, fg=status_color)}")
            click.echo(f"Started: {run.created_at}")
            click.echo(f"Duration: {run.duration} seconds")
            if run.error_message:
                click.echo(f"Error: {run.error_message}")
            click.echo("-" * 40)

    except Exception as e:
        logger.error(f"Error checking scraper runs: {e}")
        raise click.ClickException(str(e))


@scraper.command()
@with_appcontext
def clear_runs():
    """Clear all scraper run records"""
    try:
        count = ScraperRun.query.delete()
        db.session.commit()
        click.echo(f"Cleared {count} scraper run records")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing scraper runs: {e}")
        raise click.ClickException(str(e))


def register_commands(app):
    """Register CLI commands with the Flask app"""
    app.cli.add_command(scraper)
