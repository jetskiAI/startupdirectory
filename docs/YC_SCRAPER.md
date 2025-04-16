# Y Combinator Scraper

The Y Combinator scraper is designed to collect startup data from the Y Combinator directory. This document explains how it works and how to use it.

## Overview

The scraper uses Selenium to fetch data about startups that have participated in the Y Combinator accelerator program. It collects comprehensive information including:

- Company details (name, description, URL, logo)
- YC batch information (W23, S23, etc.)
- Company status (active, acquired, public)
- Industry tags
- Team size and location
- Founder information

## Key Features

- **Incremental Updates**: Only adds new companies or updates changed information
- **Change Tracking**: Records statistics about added, updated, and unchanged startups
- **Run History**: Tracks when scrapes happen with detailed statistics
- **Smart Location Detection**: Identifies and validates geographic location data
- **Batch Processing**: Can filter by year or specific batches (W23, S23, etc.)

## Usage Guide

### Running the Scraper

There are several ways to run the scraper:

#### Method 1: Flask CLI (Recommended for most uses)

```bash
# Run a normal update for all available startups
flask scrapers run

# Filter startups by specific year
flask scrapers run --year=2023

# Run with browser visible (for debugging)
flask scrapers run --no-headless

# Adjust wait time for slower connections
flask scrapers run --wait-time=15
```

#### Method 2: Standalone Script

```bash
# Run the script directly
python scripts/run_selenium_scraper.py

# Filter by year
python scripts/run_selenium_scraper.py --year=2023

# Limit the number of startups to process (useful for testing)
python scripts/run_selenium_scraper.py --limit=50
```

#### Method 3: From Python Code

```python
from app.scrapers.selenium_yc_scraper import SeleniumYCScraper

scraper = SeleniumYCScraper()
startups = scraper.fetch_startups(
    year=2023,        # Optional: Filter by year
    headless=True,    # Optional: Run browser headlessly
    wait_time=10,     # Optional: Wait time for page loading
    limit=100         # Optional: Max startups to process
)
```

### Viewing the Scraped Data

To see the startups in the database:

```bash
# View all startups (paginated)
python app/scripts/db_viewer.py

# Filter by year
python app/scripts/db_viewer.py --year=2023

# Search by name
python app/scripts/db_viewer.py --name="AI"

# Filter by batch
python app/scripts/db_viewer.py --batch="W23"

# Navigate to specific page
python app/scripts/db_viewer.py --page=2

# Disable colored output
python app/scripts/db_viewer.py --no-color
```

### Tracking Scraper Status

To check scraper run history:

```bash
# View recent scraper runs (last 7 days)
flask scrapers check-runs

# View runs from a longer period
flask scrapers check-runs --days=30
```

### Database Management

```bash
# Clear all scraper run records (but keep the startup data)
flask scrapers clear-runs

# Reset entire database
python scripts/clear_database.py

# Keep scraper run history when clearing database
python scripts/clear_database.py --keep-runs

# Analyze database contents in detail
python app/scripts/db_inspector.py
```

## Implementation Details

### Smart Location Detection

The scraper implements advanced location detection to correctly identify and separate:

- Company names
- Geographic locations
- Descriptions

This helps ensure clean data for analytics and display.

### Database Schema

The scraped data is stored in three main tables:

- `startups` - Company information and metadata
- `founders` - Founder details with relationships to companies
- `scraper_runs` - History of scraper executions

### Troubleshooting

If the scraper fails:

1. **Common Issues**:

   - Selenium ChromeDriver needs to be compatible with your Chrome version
   - Y Combinator may have updated their site structure
   - Network timeouts due to slow connections

2. **Solutions**:

   - Try increasing `--wait-time` parameter
   - Use `--no-headless` to see what's happening in the browser
   - Check Y Combinator's website structure hasn't changed
   - Start with a small batch using `--limit=10` for testing

3. **Debugging**:
   - Check logs for error messages
   - Run with visible browser (`--no-headless`)
   - Verify the ChromeDriver is up to date

## Development Notes

To extend the scraper functionality:

1. The main implementation is in `app/scrapers/selenium_yc_scraper.py`
2. Browser automation logic is in the `_scrape_with_selenium()` method
3. Data cleaning and processing is handled by `process_startup_data()` and helper methods
4. Database integration is managed by `_save_startup_to_db()`

For complex data transformations, see the location detection methods like `_extract_location()` and `validate_location()`.
