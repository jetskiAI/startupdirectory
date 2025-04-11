import click
from app.scrapers.selenium_yc_scraper import SeleniumYCScraper

# Create a CLI group for scraper commands
cli = click.Group(name="scrapers")


@click.command("scrape-yc-selenium")
@click.option("--year", default=None, type=int, help="Filter by year (optional)")
def scrape_yc_selenium(year):
    """Scrape YC startups from their website using Selenium"""
    click.echo("Starting Selenium-based YC scraper...")

    scraper = SeleniumYCScraper()
    startups = scraper.fetch_startups(year=year)

    # Print the scraping statistics
    click.echo(f"Scraping completed. Statistics:")
    click.echo(f"Total companies processed: {scraper.stats['total']}")
    click.echo(f"New companies added: {scraper.stats['added']}")
    click.echo(f"Existing companies updated: {scraper.stats['updated']}")
    click.echo(f"Unchanged companies: {scraper.stats['unchanged']}")

    if scraper.stats["total"] == 0:
        click.echo(
            "Warning: No startups were found or processed. Check the log for errors."
        )


@click.command("scrape-yc")
@click.option("--year", default=None, type=int, help="Filter by year (optional)")
@click.option(
    "--no-headless", is_flag=True, help="Run with visible browser (for debugging)"
)
@click.option(
    "--wait-time",
    default=10,
    type=int,
    help="Seconds to wait for content to load (default: 10)",
)
def scrape_yc(year, no_headless, wait_time):
    """Scrape YC startups from their website (uses Selenium)"""
    # This is just a wrapper around the selenium scraper for easier migration
    headless = not no_headless
    mode = "visible browser" if not headless else "headless mode"
    click.echo(
        f"Starting YC scraper (Selenium-based) in {mode} with {wait_time}s wait time..."
    )

    # Create and run the selenium scraper directly instead of calling the other function
    scraper = SeleniumYCScraper()
    startups = scraper.fetch_startups(year=year, headless=headless, wait_time=wait_time)

    # Print the scraping statistics
    click.echo(f"Scraping completed. Statistics:")
    click.echo(f"Total companies processed: {scraper.stats['total']}")
    click.echo(f"New companies added: {scraper.stats['added']}")
    click.echo(f"Existing companies updated: {scraper.stats['updated']}")
    click.echo(f"Unchanged companies: {scraper.stats['unchanged']}")

    if scraper.stats["total"] == 0:
        click.echo(
            "Warning: No startups were found or processed. Check the log for errors."
        )


# Register commands
cli.add_command(scrape_yc_selenium)
cli.add_command(scrape_yc)

if __name__ == "__main__":
    cli()
