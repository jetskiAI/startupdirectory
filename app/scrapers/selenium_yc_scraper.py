import requests
import re
import time
import random
import logging
from bs4 import BeautifulSoup
from datetime import datetime
import traceback

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from app.scrapers.base_scraper import BaseScraper
from app.models.startup import Startup, Founder
from app.models.db import db
from app.utils.scraper_utils import create_scraper_run, complete_scraper_run

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SeleniumYCScraper(BaseScraper):
    """Y Combinator startup data scraper using Selenium"""

    def __init__(self):
        super().__init__()
        self.source_name = "YC"
        self.base_url = "https://www.ycombinator.com/companies"

        # For tracking progress
        self.total_startups = 0
        self.processed_startups = 0

        # For tracking changes
        self.stats = {"added": 0, "updated": 0, "unchanged": 0, "total": 0}
        self.current_run = None

    def fetch_startups(self, year=None, track_run=True):
        """
        Fetch startups from Y Combinator

        Args:
            year (int, optional): Filter startups by year
            track_run (bool): Whether to track this run in the database

        Returns:
            list: List of startup dictionaries
        """
        logger.info(
            f"Starting to scrape YC startups with Selenium for year: {year or 'all'}"
        )

        # Create scraper run record if tracking enabled
        if track_run:
            try:
                self.current_run = create_scraper_run(self.source_name, db)
                logger.info(f"Created scraper run #{self.current_run.id}")
            except Exception as e:
                logger.error(f"Failed to create scraper run record: {e}")
                self.current_run = None

        try:
            # Use Selenium to scrape the actual website
            startups = self._scrape_with_selenium(year)

            # Complete run if tracking enabled
            if track_run and self.current_run:
                complete_scraper_run(self.current_run.id, "success", self.stats, db=db)

            return startups

        except Exception as e:
            logger.error(f"Error fetching YC startups: {e}")
            logger.error(traceback.format_exc())

            # Record failure if tracking enabled
            if track_run and self.current_run:
                complete_scraper_run(
                    self.current_run.id,
                    "failed",
                    self.stats,
                    error_message=str(e),
                    db=db,
                )

            return []

    def _scrape_with_selenium(self, year=None):
        """Scrape YC startups using Selenium for browser automation"""
        logger.info("Starting Selenium-based web scraping...")
        all_startups = []

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Set up the driver
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=chrome_options
            )

            # Build the URL - if year is provided, filter by batch
            url = self.base_url
            if year:
                # YC uses W/S prefix with 2-digit year (e.g., W21, S21)
                short_year = str(year)[-2:]
                url = f"{url}?batch=W{short_year},S{short_year}"
                logger.info(
                    f"Filtering by year: {year} (batches W{short_year}, S{short_year})"
                )

            # Navigate to the YC companies page
            logger.info(f"Navigating to {url}")
            driver.get(url)

            # Wait for the page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            # Log page title and URL to confirm we're in the right place
            logger.info(f"Page title: {driver.title}")
            logger.info(f"Current URL: {driver.current_url}")

            # Allow time for JavaScript to render content
            time.sleep(5)

            # Take screenshot for debugging
            screenshot_path = "yc_screenshot.png"
            driver.save_screenshot(screenshot_path)
            logger.info(f"Saved screenshot to {screenshot_path}")

            # Try to identify company containers
            potential_selectors = [
                ".Directory_companyList__R0sxr > div",  # YC companies are in this container as of 2023
                ".company-card",
                ".company",
                "[data-testid='company-card']",
                ".startup-item",
                "div[role='list'] > div",  # Generic list container
            ]

            company_elements = []
            used_selector = None

            for selector in potential_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if (
                    elements and len(elements) > 5
                ):  # Ensure we found a reasonable number of companies
                    company_elements = elements
                    used_selector = selector
                    logger.info(
                        f"Found {len(elements)} companies using selector: {selector}"
                    )
                    break

            if not company_elements:
                logger.warning(
                    "No company elements found with standard selectors. Attempting to analyze page structure..."
                )
                # Try to save the HTML for analysis
                with open("yc_page.html", "w") as f:
                    f.write(driver.page_source)
                logger.info("Saved page HTML to yc_page.html for analysis")

                # Try another approach - look for elements with links and text
                elements = driver.find_elements(By.CSS_SELECTOR, "div")
                potential_companies = []

                for elem in elements:
                    # Look for elements that might be company cards
                    if elem.text and len(elem.text.split("\n")) >= 2:
                        links = elem.find_elements(By.TAG_NAME, "a")
                        if links:
                            potential_companies.append(elem)

                if potential_companies and len(potential_companies) > 5:
                    company_elements = potential_companies
                    logger.info(
                        f"Found {len(potential_companies)} potential company elements using fallback method"
                    )

            # Process each company element
            for i, element in enumerate(company_elements):
                try:
                    # Extract text content
                    text_content = element.text.strip()
                    if not text_content:
                        continue

                    logger.info(f"Processing company {i+1}/{len(company_elements)}")

                    # Extract lines of text
                    lines = text_content.split("\n")

                    # Basic parsing - first line is usually company name
                    company_name = lines[0] if lines else "Unknown"
                    # Second line often contains description
                    description = lines[1] if len(lines) > 1 else ""

                    # Create company data structure
                    company_data = {
                        "name": company_name,
                        "description": description,
                        "batch": "",
                        "url": "",
                        "logoUrl": "",
                        "tags": [],
                        "status": "ACTIVE",  # Default status
                        "teamSize": "",
                        "location": "",
                        "founders": [],
                    }

                    # Try to extract more details
                    try:
                        # Find links
                        links = element.find_elements(By.TAG_NAME, "a")
                        if links:
                            # First link is often the company URL
                            for link in links:
                                href = link.get_attribute("href")
                                if href and "ycombinator.com" not in href:
                                    company_data["url"] = href
                                    break

                        # Find images (logo)
                        images = element.find_elements(By.TAG_NAME, "img")
                        if images:
                            company_data["logoUrl"] = (
                                images[0].get_attribute("src") or ""
                            )

                        # Look for batch info in text
                        batch_pattern = r"\b([WS]\d{2})\b"  # Pattern for W20, S21, etc.
                        batch_matches = re.findall(batch_pattern, text_content)
                        if batch_matches:
                            company_data["batch"] = batch_matches[0]
                        elif year:
                            # If batch not found but year was specified, make educated guess
                            short_year = str(year)[-2:]
                            company_data["batch"] = (
                                f"W{short_year}"  # Default to winter batch
                            )

                        # Extract additional info - look for common patterns
                        for line in lines[2:]:  # Skip name and description
                            # Location often contains city names
                            location_indicators = [
                                "San Francisco",
                                "New York",
                                "Boston",
                                "Remote",
                                "USA",
                                "London",
                            ]
                            if any(
                                indicator in line for indicator in location_indicators
                            ):
                                company_data["location"] = line.strip()

                            # Tags/categories
                            if len(line.split(",")) > 1 and len(line) < 50:
                                company_data["tags"] = [
                                    tag.strip() for tag in line.split(",")
                                ]

                    except Exception as detail_e:
                        logger.error(
                            f"Error extracting details for company {company_name}: {detail_e}"
                        )

                    # Add to our collection if it has a valid name
                    if company_data["name"] and company_data["name"] != "Unknown":
                        all_startups.append(company_data)
                        logger.info(f"Added company: {company_data['name']}")

                except Exception as e:
                    logger.error(f"Error processing company element {i+1}: {e}")

            logger.info(f"Extracted {len(all_startups)} companies from YC website")

            # If we found very few companies, attempt to scroll and load more
            if len(all_startups) < 10:
                logger.info(
                    "Found fewer companies than expected. Attempting to scroll and load more..."
                )

                # Scroll to load more content
                for _ in range(5):
                    driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    time.sleep(2)  # Wait for content to load

                # Take another screenshot after scrolling
                driver.save_screenshot("yc_scrolled.png")
                logger.info("Saved screenshot after scrolling to yc_scrolled.png")

                # Try to find elements again
                if used_selector:
                    company_elements = driver.find_elements(
                        By.CSS_SELECTOR, used_selector
                    )
                    logger.info(
                        f"After scrolling, found {len(company_elements)} companies"
                    )

                    # Process any new elements
                    # (Implement similar extraction logic as above)

        except Exception as e:
            logger.error(f"Error in Selenium scraper: {e}")
            logger.error(traceback.format_exc())

        finally:
            # Clean up
            try:
                driver.quit()
                logger.info("Closed Selenium browser")
            except Exception:
                pass

        # Process the raw data
        logger.info(f"Processing {len(all_startups)} startups...")
        processed_startups = []

        for idx, startup in enumerate(all_startups):
            try:
                self.processed_startups = idx + 1
                processed_data = self.process_startup_data(startup)

                # Save to database (this tracks changes)
                self._save_startup_to_db(processed_data)

                processed_startups.append(processed_data)

                # Log progress periodically
                if (idx + 1) % 10 == 0 or (idx + 1) == len(all_startups):
                    logger.info(f"Processed {idx + 1}/{len(all_startups)} startups")

            except Exception as e:
                logger.error(
                    f"Error processing startup {startup.get('name', 'Unknown')}: {e}"
                )

        # Update total count in stats
        self.stats["total"] = len(processed_startups)
        logger.info(f"Successfully processed {len(processed_startups)} startups")
        logger.info(
            f"Stats: Added={self.stats['added']}, Updated={self.stats['updated']}, Unchanged={self.stats['unchanged']}"
        )

        return processed_startups

    def process_startup_data(self, raw_data):
        """
        Process raw YC startup data into standardized format

        Args:
            raw_data (dict): Raw startup data

        Returns:
            dict: Processed startup data
        """
        # Extract year from batch (e.g., "W21" -> 2021)
        batch = raw_data.get("batch", "")
        year = None
        if batch:
            match = re.search(r"([WS])(\d{2})", batch)
            if match:
                year_short = match.group(2)
                # Convert 2-digit year to 4-digit year (assuming 20xx for now)
                year = int("20" + year_short)

        # If we couldn't extract a year, set a default current year
        # This ensures the NOT NULL constraint is satisfied
        if year is None:
            current_year = datetime.now().year
            year = current_year
            logger.info(
                f"Setting default year {current_year} for startup: {raw_data.get('name', 'Unknown')}"
            )

        # Process industry tags
        tags = raw_data.get("tags", [])
        if tags:
            tags_str = ", ".join(tags)
        else:
            tags_str = None

        # Create standardized startup data
        startup_data = {
            "name": raw_data.get("name", ""),
            "description": raw_data.get("description", ""),
            "year_founded": year,
            "url": raw_data.get("url", ""),
            "logo_url": raw_data.get("logoUrl", ""),
            "source": self.source_name,
            "industry": tags[0] if tags else None,  # Use first tag as primary industry
            "batch": batch,
            "status": "active",  # Default status since we can't easily determine this
            "location": raw_data.get("location", ""),
            "tags": tags_str,
            "team_size": 0,  # Can't easily determine from scraping
            "founders": [],  # We don't have founder data from basic scraping
        }

        return startup_data

    def _save_startup_to_db(self, startup_data):
        """
        Save startup data to database, tracking if it's new or updated

        Args:
            startup_data (dict): Processed startup data

        Returns:
            tuple: (Startup object, bool indicating if created)
        """
        # Extract founders info (if any)
        founders_data = startup_data.pop("founders", [])

        # Check if startup already exists (by name and batch/year)
        existing_startup = Startup.query.filter_by(
            name=startup_data["name"], batch=startup_data.get("batch")
        ).first()

        is_updated = False
        is_created = False

        if existing_startup:
            # Check if any data has changed
            data_changed = False
            for key, value in startup_data.items():
                if getattr(existing_startup, key) != value:
                    setattr(existing_startup, key, value)
                    data_changed = True

            if data_changed:
                logger.info(f"Updating existing startup: {startup_data['name']}")
                is_updated = True
            else:
                logger.info(f"Startup unchanged: {startup_data['name']}")

            startup = existing_startup
        else:
            logger.info(f"Creating new startup: {startup_data['name']}")
            # Create new startup
            startup = Startup(**startup_data)
            db.session.add(startup)
            is_created = True

        # We need to flush to get the startup ID for founders
        db.session.flush()

        # Process founders (if any)
        for founder_data in founders_data:
            # Check if founder already exists for this startup
            existing_founder = Founder.query.filter_by(
                name=founder_data["name"], startup_id=startup.id
            ).first()

            if existing_founder:
                # Check if founder data has changed
                founder_changed = False
                for key, value in founder_data.items():
                    if getattr(existing_founder, key) != value:
                        setattr(existing_founder, key, value)
                        founder_changed = True

                if founder_changed and not is_updated:
                    is_updated = (
                        True  # Mark startup as updated if only founder data changed
                    )
            else:
                # Create new founder
                new_founder = Founder(**founder_data)
                new_founder.startup_id = startup.id
                db.session.add(new_founder)
                if not is_updated and not is_created:
                    is_updated = True  # Mark as updated if we're adding a new founder

        db.session.commit()

        # Update statistics based on outcome
        if is_created:
            self.stats["added"] += 1
        elif is_updated:
            self.stats["updated"] += 1
        else:
            self.stats["unchanged"] += 1

        return startup, is_created
