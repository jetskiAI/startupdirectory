import click
from app.scrapers.yc_scraper import YCombinatorScraper
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


cli.add_command(scrape_yc_selenium)

if __name__ == "__main__":
    cli()
