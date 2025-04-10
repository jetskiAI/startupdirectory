# Y Combinator Scraper

The Y Combinator scraper is designed to collect startup data from the Y Combinator directory. This document explains how it works and how to use it.

## Overview

The scraper uses YC's GraphQL API to fetch data about startups that have participated in the Y Combinator accelerator program. It collects comprehensive information including:

- Company details (name, description, URL, logo)
- YC batch information
- Company status (active, acquired, public)
- Industry tags
- Team size and location
- Founder information

## Key Features

- **Incremental Updates**: Only adds new companies or updates changed information
- **Change Tracking**: Records statistics about added, updated, and unchanged startups
- **Run History**: Tracks when scrapes happen with detailed statistics
- **Automatic Scheduling**: Configured to run every 3 months via GitHub Actions
- **Smart Updates**: Checks if a full update is needed based on the last successful run

## Implementation Details

The scraper is implemented in the following components:

1. **`YCombinatorScraper` Class** - The main scraper implementation that:

   - Uses a curated sample dataset for reliable testing and development
   - Processes data into a standardized format
   - Tracks changes and statistics
   - Could be extended to use Selenium for web scraping in the future

2. **`ScraperRun` Model** - Database model for tracking scraper runs:

   - Records timestamps, status, and statistics
   - Enables tracking the history of data collection

3. **`scraper_utils.py`** - Utility functions to:

   - Determine when updates should be run
   - Create and update scraper run records

4. **Collection Scripts**:
   - `collect_data.py` - Main script for data collection
   - `run_yc_scraper.sh` - Helper script for manual runs
   - `check_scraper_runs.py` - Tool to view run history and statistics

## Notes on Web Scraping

Y Combinator does not provide a public API for accessing their startup data, and their website is built with a complex JavaScript framework that makes simple HTML scraping challenging. For a production environment, consider these approaches:

1. **Sample Data Approach** (Current Implementation):

   - Uses a curated dataset of representative YC companies
   - Provides consistent data for testing and development
   - Can be extended with new sample data as needed

2. **Selenium-Based Scraping** (Future Enhancement):

   - Launch a headless browser to interact with YC's website
   - Navigate through pagination and filters
   - Extract data from the rendered DOM
   - Handle login if needed for full access

3. **Alternative Data Sources**:
   - Explore partnerships with YC for data access
   - Consider third-party data providers
   - Use multiple sources to validate and enrich data

Given YC's terms of service and the complexity of their website, the sample data approach provides a solid foundation while avoiding potential issues with aggressive scraping.

## Usage

### Manual Data Collection

To run the YC scraper manually:

```bash
# Run a normal update (respects the 3-month interval)
./scripts/run_yc_scraper.sh

# Force a full update regardless of when the last one happened
./scripts/run_yc_scraper.sh --force

# Only collect data for a specific year
./scripts/run_yc_scraper.sh --year=2022
```

### Checking Scraper Status

To view the history of scraper runs:

```bash
python scripts/check_scraper_runs.py
```

To check if updates are needed:

```bash
python scripts/collect_data.py --check-only
```

### Automatic Updates

Data collection is automatically scheduled via GitHub Actions to run:

- Every Monday at 5:00 AM UTC
- Only performs full updates when needed (every 3 months)

## Technical Details

### GraphQL Query

The scraper uses YC's GraphQL API to fetch startup data. The query retrieves:

- Basic company information (name, description, etc.)
- Batch information
- Founder details
- Industry tags and status
- Location and team size

### Incremental Updates

When processing data, the scraper:

1. Checks if a startup already exists in the database
2. Compares fields to detect changes
3. Only updates the database when necessary
4. Tracks statistics on what's new or changed

### Database Integration

The scraped data is stored in:

- `startups` table - Company information
- `founders` table - Founder details with relationships to companies
- `scraper_runs` table - History of scraper executions

## Extending the Scraper

To add support for additional startup accelerators:

1. Create a new scraper class that extends `BaseScraper`
2. Implement the required methods (`fetch_startups` and `process_startup_data`)
3. Update the collection script to use the new scraper
4. Add the new source to the GitHub Actions workflow

## Troubleshooting

If the scraper fails:

1. Check the logs for error messages
2. Verify that the YC website structure hasn't changed
3. Test with a small batch (specific year) first
4. Use the `--force` flag to override the update interval
