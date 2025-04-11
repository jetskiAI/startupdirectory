import requests
import re
import time
import random
import logging
import os
import glob
import traceback
from bs4 import BeautifulSoup
from datetime import datetime
from flask import current_app

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

    def fetch_startups(self, year=None, track_run=True, headless=True, wait_time=10):
        """
        Fetch startups from Y Combinator

        Args:
            year (int, optional): Filter startups by year
            track_run (bool): Whether to track this run in the database
            headless (bool): Whether to run the browser in headless mode
            wait_time (int): How many seconds to wait for content to load

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
            startups = self._scrape_with_selenium(
                year, headless=headless, wait_time=wait_time
            )

            # If scraping completed successfully, delete all screenshots
            if startups:
                screenshot_pattern = "yc_*.png"
                screenshot_count = 0
                for screenshot in glob.glob(screenshot_pattern):
                    try:
                        os.remove(screenshot)
                        screenshot_count += 1
                    except Exception as e:
                        logger.warning(f"Error removing screenshot {screenshot}: {e}")

                if screenshot_count > 0:
                    logger.info(
                        f"Successfully removed {screenshot_count} screenshots after successful scrape"
                    )

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

    def _scrape_with_selenium(self, year=None, headless=True, wait_time=10):
        """Scrape YC startups using Selenium for browser automation"""
        logger.info("Starting Selenium-based web scraping...")
        all_startups = []

        # Clean up old screenshots
        # Delete any existing yc_filtered_*.png screenshots
        screenshot_pattern = "yc_filtered_*.png"
        for old_screenshot in glob.glob(screenshot_pattern):
            try:
                os.remove(old_screenshot)
                logger.info(f"Removed old screenshot: {old_screenshot}")
            except Exception as e:
                logger.warning(f"Error removing old screenshot {old_screenshot}: {e}")

        # Configure Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        # Use a more human-like user agent
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        )

        # Set up the driver
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=chrome_options
            )

            batches = []
            if year:
                # Use the batch parameter to filter by year
                # YC uses batches like W22, S22 for 2022
                short_year = str(year)[-2:]
                # Create separate batches for winter and summer sessions
                batches = [f"W{short_year}", f"S{short_year}"]
                logger.info(
                    f"Will scrape each batch individually: {', '.join(batches)}"
                )
            else:
                # If no year is provided, just use the base URL once
                batches = [None]

            # Process each batch separately
            for batch in batches:
                # Navigate directly with filter URL parameters
                url = self.base_url
                if batch:
                    url = f"{url}?batch={batch}"
                    logger.info(f"Scraping batch: {batch} at URL: {url}")
                else:
                    logger.info(f"Scraping all batches at URL: {url}")

                logger.info(f"Navigating to {url}")
                driver.get(url)

                # Wait for the page to load
                wait = WebDriverWait(
                    driver, wait_time + 5
                )  # Add a buffer to the wait time
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

                # Log page title and URL to confirm we're in the right place
                logger.info(f"Page title: {driver.title}")
                logger.info(f"Current URL: {driver.current_url}")

                # Allow time for JavaScript to render content
                logger.info(
                    f"Waiting {wait_time} seconds for JavaScript to render content..."
                )
                time.sleep(wait_time)

                # Take screenshot for debugging
                screenshot_prefix = batch if batch else "all"
                screenshot_path = f"yc_filtered_{screenshot_prefix}.png"
                driver.save_screenshot(screenshot_path)
                logger.info(f"Saved screenshot to {screenshot_path}")

                # Use a direct DOM-based approach to extract companies
                logger.info("Trying direct DOM extraction...")
                company_links = driver.find_elements(
                    By.CSS_SELECTOR, 'a[class*="_company_"]'
                )

                if not company_links or len(company_links) < 5:
                    logger.warning(
                        f"Found only {len(company_links) if company_links else 0} company links with primary selector, trying alternatives..."
                    )
                    # Try alternative selectors
                    company_links = driver.find_elements(
                        By.CSS_SELECTOR, 'a[href^="/companies/"]'
                    )

                    if not company_links or len(company_links) < 5:
                        logger.warning(
                            "Still not enough company links, trying one more selector..."
                        )
                        # One more attempt with a broader selector
                        company_links = driver.find_elements(
                            By.CSS_SELECTOR, 'div[class*="rightCol"] a'
                        )

                if company_links and len(company_links) > 0:
                    logger.info(
                        f"Found {len(company_links)} potential company links for batch {batch or 'all'}"
                    )

                    for i, link in enumerate(company_links):
                        try:
                            # Extract HTML to debug
                            if i < 3:  # Just log the first few for debugging
                                logger.info(
                                    f"Company link {i+1} HTML: {link.get_attribute('outerHTML')[:200]}..."
                                )

                            # Extract text content
                            text_content = link.text.strip()
                            if not text_content:
                                continue

                            logger.info(
                                f"Processing company {i+1}/{len(company_links)}"
                            )

                            # Extract company name - assume it's the first line or has a specific class
                            lines = text_content.split("\n")
                            company_name = lines[0] if lines else ""

                            # Skip obvious non-company elements
                            skip_names = [
                                "About",
                                "Contact",
                                "FAQ",
                                "Menu",
                                "Home",
                                "Jobs",
                            ]
                            if any(
                                skip_word.lower() in company_name.lower()
                                for skip_word in skip_names
                            ):
                                continue

                            # Get description - typically second line or has specific class
                            description = lines[1] if len(lines) > 1 else ""

                            # Get location if present (typically has "location" in class name or appears after name)
                            location = ""
                            for line in lines[1:]:
                                if any(
                                    loc in line
                                    for loc in [
                                        "San Francisco",
                                        "New York",
                                        "Remote",
                                        "London",
                                        "Berlin",
                                        "Singapore",
                                        "Tel Aviv",
                                    ]
                                ):
                                    location = line
                                    break

                            # Try to extract batch (S22, W22, etc.) and industry tags
                            batch = ""
                            tags = []

                            # Check for batch pattern in text
                            batch_match = re.search(r"([WS]\d{2})", text_content)
                            if batch_match:
                                batch = batch_match.group(0)

                            # Create company data structure
                            company_data = {
                                "name": company_name.strip(),
                                "description": description.strip(),
                                "batch": batch,
                                "url": link.get_attribute("href") or "",
                                "logoUrl": "",
                                "tags": tags,
                                "status": "ACTIVE",  # Default status
                                "teamSize": "",
                                "location": location.strip(),
                                "founders": [],
                            }

                            # Try to find logo image
                            try:
                                img = link.find_element(By.TAG_NAME, "img")
                                if img:
                                    company_data["logoUrl"] = (
                                        img.get_attribute("src") or ""
                                    )
                            except:
                                pass

                            # Visit the individual company page to get more details
                            if (
                                company_data["url"]
                                and "ycombinator.com" in company_data["url"]
                            ):
                                try:
                                    logger.info(
                                        f"Visiting company page: {company_data['url']}"
                                    )

                                    # Open the company page in a new tab
                                    driver.execute_script(
                                        f"window.open('{company_data['url']}', '_blank');"
                                    )

                                    # Switch to the new tab
                                    driver.switch_to.window(driver.window_handles[1])

                                    # Wait for page to load
                                    wait = WebDriverWait(driver, wait_time)
                                    wait.until(
                                        EC.presence_of_element_located(
                                            (By.TAG_NAME, "body")
                                        )
                                    )

                                    # Allow time for page to render fully
                                    time.sleep(3)

                                    # Extract founders information
                                    try:
                                        # Look for founder elements - adjust selectors based on YC's actual HTML structure
                                        founder_elements = driver.find_elements(
                                            By.CSS_SELECTOR,
                                            'div[class*="founder"], div[class*="team"]',
                                        )

                                        if not founder_elements:
                                            # Try alternate selectors
                                            founder_elements = driver.find_elements(
                                                By.XPATH,
                                                '//h3[contains(text(), "Founder") or contains(text(), "Team")]/following-sibling::div',
                                            )

                                        for element in founder_elements:
                                            try:
                                                founder_name = element.find_element(
                                                    By.CSS_SELECTOR, "h3, h4, strong"
                                                ).text.strip()

                                                # Try to get title if available
                                                title = ""
                                                try:
                                                    title_elem = element.find_element(
                                                        By.CSS_SELECTOR, "p, span"
                                                    )
                                                    title = title_elem.text.strip()
                                                except:
                                                    pass

                                                # Try to get LinkedIn URL if available
                                                linkedin_url = ""
                                                try:
                                                    linkedin_link = element.find_element(
                                                        By.XPATH,
                                                        './/a[contains(@href, "linkedin.com")]',
                                                    )
                                                    linkedin_url = (
                                                        linkedin_link.get_attribute(
                                                            "href"
                                                        )
                                                    )
                                                except:
                                                    pass

                                                if founder_name:
                                                    company_data["founders"].append(
                                                        {
                                                            "name": founder_name,
                                                            "title": title,
                                                            "linkedin_url": linkedin_url,
                                                            "twitter_url": "",
                                                            "github_url": "",
                                                            "email": "",
                                                            "bio": "",
                                                            "role_type": "",
                                                            "background": "",
                                                        }
                                                    )
                                                    logger.info(
                                                        f"Found founder: {founder_name}"
                                                    )
                                            except Exception as fe:
                                                logger.error(
                                                    f"Error processing founder element: {fe}"
                                                )
                                    except Exception as e:
                                        logger.error(f"Error extracting founders: {e}")

                                    # Extract additional tags
                                    try:
                                        # Look for tag elements
                                        tag_elements = driver.find_elements(
                                            By.CSS_SELECTOR,
                                            'span[class*="tag"], div[class*="tag"]',
                                        )

                                        for tag_elem in tag_elements:
                                            tag_text = tag_elem.text.strip()
                                            if (
                                                tag_text
                                                and tag_text not in company_data["tags"]
                                            ):
                                                company_data["tags"].append(tag_text)
                                                logger.info(f"Found tag: {tag_text}")
                                    except Exception as e:
                                        logger.error(f"Error extracting tags: {e}")

                                    # Close the company page tab and switch back to the main tab
                                    driver.close()
                                    driver.switch_to.window(driver.window_handles[0])

                                except Exception as e:
                                    logger.error(f"Error visiting company page: {e}")
                                    # Make sure to switch back to the main tab if there's an error
                                    if len(driver.window_handles) > 1:
                                        driver.close()
                                        driver.switch_to.window(
                                            driver.window_handles[0]
                                        )

                            # Add to our collection if it has a valid name and doesn't look like a UI element
                            if (
                                company_data["name"]
                                and company_data["name"] != "Unknown"
                                and len(company_data["name"]) > 2
                            ):
                                all_startups.append(company_data)
                                logger.info(f"Added company: {company_data['name']}")
                        except Exception as e:
                            logger.error(f"Error processing company link {i+1}: {e}")
                            continue
                else:
                    logger.warning("No company links found in the DOM")

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
