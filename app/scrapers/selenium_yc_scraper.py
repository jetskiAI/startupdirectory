import re
import time
import logging
import unicodedata

import traceback
from datetime import datetime

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
    """Y Combinator startup data scraper using Selenium with dynamic location detection"""

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

        # Initialize with minimal fallback location data
        # These will be supplemented with database-driven data
        self.common_location_prefixes = ["San", "New", "Los"]
        self.known_locations = set()

        # Initialize geographic indicators
        self._init_geographic_indicators()

        # Load known locations from the database
        self.refresh_location_data()

    def refresh_location_data(self):
        """
        Load known locations from the database to improve location detection
        Should be called periodically to keep location data fresh
        """
        try:
            # Query distinct locations from the database
            locations = db.session.query(Startup.location).distinct().all()

            # Extract location strings from query results and filter out invalid ones
            location_strings = []
            for loc in locations:
                if loc[0] and len(loc[0]) > 2:
                    # Filter out descriptions that were mistakenly stored as locations
                    if not self._is_description_not_location(loc[0]):
                        location_strings.append(loc[0])

            # Store in a set for efficient lookups
            self.known_locations = set(location_strings)

            # Extract common prefixes from locations for pattern matching
            prefixes = set()
            for location in location_strings:
                words = location.split()
                if words and len(words[0]) >= 2:
                    prefixes.add(words[0])

            # Update our common location prefixes with database-derived ones
            # But keep the essential fallbacks
            self.common_location_prefixes = list(
                set(self.common_location_prefixes) | prefixes
            )

            logger.info(
                f"Refreshed location data: {len(self.known_locations)} locations, {len(self.common_location_prefixes)} prefixes"
            )
        except Exception as e:
            logger.error(f"Failed to refresh location data: {e}")

    def _init_geographic_indicators(self):
        """Initialize lists of geographic indicators for better location validation"""
        # Common country names and codes
        self.countries = {
            "USA",
            "United States",
            "Canada",
            "Mexico",
            "Brazil",
            "UK",
            "United Kingdom",
            "Germany",
            "France",
            "Italy",
            "Spain",
            "China",
            "Japan",
            "India",
            "Australia",
            "Russia",
            "South Korea",
            "Singapore",
            "Indonesia",
            "Malaysia",
            "Thailand",
            "Vietnam",
            "Philippines",
            "Nigeria",
            "Kenya",
            "South Africa",
            "Egypt",
            "Argentina",
            "Chile",
            "Colombia",
            "Peru",
            "Venezuela",
            "Israel",
            "Turkey",
            "Saudi Arabia",
            "UAE",
            "Pakistan",
            "Bangladesh",
            "New Zealand",
        }

        # Add abbreviated regions and economic zones
        self.regions = {
            "EU",
            "APAC",
            "EMEA",
            "LATAM",
            "MENA",
            "DACH",
            "ANZ",
            "BENELUX",
            "ASEAN",
            "CIS",
            "GCC",
            "US",
        }
        self.countries.update(self.regions)

        # Common state/province codes and names
        self.states_provinces = {
            # US States
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
            "DC",
            # Canadian Provinces
            "AB",
            "BC",
            "MB",
            "NB",
            "NL",
            "NS",
            "NT",
            "NU",
            "ON",
            "PE",
            "QC",
            "SK",
            "YT",
            # Common province/state names
            "California",
            "New York",
            "Texas",
            "Florida",
            "Illinois",
            "Pennsylvania",
            "Ohio",
            "Michigan",
            "Georgia",
            "North Carolina",
            "New Jersey",
            "Virginia",
            "Washington",
            "Arizona",
            "Massachusetts",
            "Tennessee",
            "Indiana",
            "Missouri",
            "Maryland",
            "Wisconsin",
            "Minnesota",
            "Colorado",
            "Alabama",
            "South Carolina",
            "Louisiana",
            "Kentucky",
            "Oregon",
            "Oklahoma",
            "Connecticut",
            "Iowa",
            "Utah",
            "Nevada",
            "Arkansas",
            "Mississippi",
            "Kansas",
            "New Mexico",
            "Nebraska",
            "West Virginia",
            "Idaho",
            "Hawaii",
            "New Hampshire",
            "Maine",
            "Montana",
            "Rhode Island",
            "Delaware",
            "South Dakota",
            "North Dakota",
            "Alaska",
            "Vermont",
            "Wyoming",
            "Ontario",
            "Quebec",
            "British Columbia",
            "Alberta",
            "Manitoba",
            "Saskatchewan",
            "Nova Scotia",
            "New Brunswick",
        }

        # Common major international cities
        self.major_cities = {
            "New York",
            "Los Angeles",
            "Chicago",
            "Houston",
            "Phoenix",
            "Philadelphia",
            "San Antonio",
            "San Diego",
            "Dallas",
            "San Jose",
            "Austin",
            "Jacksonville",
            "Fort Worth",
            "Columbus",
            "San Francisco",
            "Charlotte",
            "Indianapolis",
            "Seattle",
            "Denver",
            "Boston",
            "Portland",
            "Las Vegas",
            "Detroit",
            "Atlanta",
            "Toronto",
            "Montreal",
            "Vancouver",
            "Calgary",
            "Ottawa",
            "Edmonton",
            "London",
            "Paris",
            "Berlin",
            "Madrid",
            "Rome",
            "Amsterdam",
            "Barcelona",
            "Vienna",
            "Munich",
            "Hamburg",
            "Milan",
            "Stockholm",
            "Dublin",
            "Brussels",
            "Sydney",
            "Melbourne",
            "Brisbane",
            "Perth",
            "Adelaide",
            "Tokyo",
            "Osaka",
            "Seoul",
            "Shanghai",
            "Beijing",
            "Hong Kong",
            "Singapore",
            "Bangkok",
            "Mumbai",
            "Delhi",
            "Bangalore",
            "Kolkata",
            "Chennai",
            "Jakarta",
            "Manila",
            "Lagos",
            "Nairobi",
            "Cairo",
            "Johannesburg",
            "Cape Town",
            "São Paulo",
            "Rio de Janeiro",
            "Brasília",
            "Mexico City",
            "Monterrey",
            "Guadalajara",
            "Bogotá",
            "Lima",
            "Santiago",
            "Buenos Aires",
            "Dubai",
            "Istanbul",
            "Moscow",
            "Tel Aviv",
        }

        # Special location terms and codes
        self.special_locations = {
            "CDMX": "Mexico City",
            "DF": "Mexico City",
            "D.F.": "Mexico City",
            "N.L.": "Nuevo León",
            "KA": "Karnataka",
            "AP": "Andhra Pradesh",
            "TN": "Tamil Nadu",
            "UP": "Uttar Pradesh",
            "UK": "United Kingdom",
            "UAE": "United Arab Emirates",
        }

        # Common location endings that indicate a geographic entity
        self.location_endings = {
            "City",
            "County",
            "District",
            "Province",
            "Region",
            "State",
            "Territory",
            "Township",
            "Town",
            "Village",
            "Municipality",
            "Metropolitan Area",
            "Metro",
            "Valley",
            "Coast",
            "Island",
            "Peninsula",
        }

    def _is_description_not_location(self, text):
        """Check if text is likely a description rather than a location"""
        if not text:
            return True

        # Check for very long text (descriptions tend to be longer)
        if len(text) > 60:
            return True

        # Check for sentence patterns
        if "." in text and len(text.split(".")) > 1:
            return True

        # Common department/business terms that are not locations
        department_terms = [
            "ENGINEERING",
            "PRODUCT",
            "DESIGN",
            "MARKETING",
            "SALES",
            "CUSTOMER",
            "SUPPORT",
            "FINANCE",
            "HR",
            "OPERATIONS",
            "TALENT",
            "TECH",
            "TEAM",
            "DEPARTMENT",
            "DIVISION",
            "MANAGEMENT",
            "STAFF",
            "LEADERSHIP",
            "CENTER",
            "GROUP",
            "DIRECTOR",
            "HEAD",
            "VP",
            "CHIEF",
            "EXECUTIVE",
        ]

        # If text contains ALL CAPS words matching department terms, it's likely not a location
        words = text.split()
        uppercase_words = [w for w in words if w.isupper() and len(w) > 2]
        if uppercase_words:
            dept_matches = sum(1 for w in uppercase_words if w in department_terms)
            if dept_matches > 0:
                return True

        # Check for common separator patterns in departments (X, Y AND Z)
        if " AND " in text.upper() or " & " in text:
            return True

        # Check for description-like phrases
        description_phrases = [
            "platform",
            "software",
            "marketplace",
            "solution",
            "service",
            "app",
            "API",
            "for",
            "that",
            "helps",
            "enables",
            "empowers",
            "building",
            "powered by",
            "industry",
            "businesses",
            "product",
            "technology",
            "the",
            "your",
            "provides",
            "offering",
        ]

        # Count how many description words/phrases are in the text
        word_count = len(text.split())
        desc_count = sum(
            1 for phrase in description_phrases if phrase.lower() in text.lower()
        )

        # If more than 25% of words are description indicators or contains multiple indicators
        if desc_count >= 2 or (desc_count > 0 and desc_count / word_count > 0.25):
            return True

        # Check for geographic indicators (if none present, might be a description)
        has_geographic_indicator = self._contains_geographic_indicator(text)
        if not has_geographic_indicator:
            return True

        return False

    def _contains_geographic_indicator(self, text):
        """Check if text contains recognizable geographic indicators"""
        if not text:
            return False

        text_parts = text.split(",")

        # Look for common country names
        for country in self.countries:
            if country in text:
                return True

        # Look for state/province codes after a comma (e.g., "City, CA")
        for part in text_parts[1:]:  # Skip the first part (likely city name)
            part = part.strip()
            if part in self.states_provinces:
                return True

            # Check for 2-letter codes with leading/trailing space
            for word in part.split():
                if word in self.states_provinces and len(word) == 2:
                    return True

        # Check for major cities
        for city in self.major_cities:
            if city in text:
                return True

        # Check for special location codes
        for code in self.special_locations:
            if code in text:
                return True

        # Check for location endings
        for ending in self.location_endings:
            if text.endswith(" " + ending):
                return True

        # Check for postal/zip code patterns
        if re.search(r"\b\d{5}(?:-\d{4})?\b", text):  # US zip code
            return True
        if re.search(r"\b[A-Z]\d[A-Z] \d[A-Z]\d\b", text):  # Canadian postal code
            return True

        return False

    def validate_location(self, potential_location):
        """
        Validate potential location with multiple checks to ensure it's an actual geographic location
        Returns a confidence score (0-100) or 0 if definitely not a location
        """
        if not potential_location:
            return 0

        # Start with base confidence score
        confidence = 0

        # Check length - locations are typically not very long
        if len(potential_location) > 50:
            return 0
        if len(potential_location) < 3:
            return 0

        # Check for uppercase words - department names are often all uppercase
        words = potential_location.split()
        uppercase_count = sum(1 for w in words if w.isupper() and len(w) > 2)
        if uppercase_count >= 2 or (len(words) <= 3 and uppercase_count == len(words)):
            # Text is likely a department or business unit, not a location
            return 0

        # First check if it's likely a description rather than a location
        if self._is_description_not_location(potential_location):
            return 0

        # Direct match with known locations - highest confidence
        if potential_location in self.known_locations:
            confidence += 80

        # Contains geographic indicators - strong signal
        if self._contains_geographic_indicator(potential_location):
            confidence += 50

        # Contains common location words
        location_words = [
            "city",
            "san",
            "new",
            "los",
            "bay",
            "north",
            "south",
            "east",
            "west",
        ]
        contains_location_word = any(
            word.lower() in potential_location.lower() for word in location_words
        )
        if contains_location_word:
            confidence += 20

        # Check for disqualifiers that indicate descriptions, not locations
        description_phrases = [
            "platform for",
            "software for",
            "marketplace for",
            "solution for",
            "the future of",
            "service for",
            "helps",
            "enables",
            "building",
            "powered by",
            "industry",
            "for businesses",
            "for enterprises",
        ]

        if any(phrase in potential_location.lower() for phrase in description_phrases):
            return 0

        # Check if contains punctuation common in descriptions
        if (
            ":" in potential_location
            or "!" in potential_location
            or "?" in potential_location
        ):
            return 0

        # Check for common location patterns (City, Country format)
        if "," in potential_location:
            confidence += 30

        # Check for postal/zip code pattern (numbers followed by city)
        if re.search(r"\d{4,6}\s+[A-Z][a-z]+", potential_location):
            confidence += 40

        # Special handling for international locations
        # Check for special location codes
        for code, location_name in self.special_locations.items():
            if code in potential_location:
                confidence += 40
                break

        # Check for South American locations with accented characters
        if re.search(r"[àáâãäåçèéêëìíîïñòóôõöùúûüýÿ]", potential_location):
            # If text has accented chars and looks like a location pattern
            if re.search(
                r"[A-Z][a-zàáâãäåçèéêëìíîïñòóôõöùúûüýÿ]+,?\s", potential_location
            ):
                confidence += 30

        # Normalize for international characters and check known locations again
        normalized = unicodedata.normalize("NFD", potential_location)
        normalized = "".join([c for c in normalized if not unicodedata.combining(c)])

        if normalized in self.known_locations:
            confidence += 50

        # Cap confidence at 100
        return min(confidence, 100)

    def _extract_location(self, driver, text_content):
        """
        Extract location information using multiple strategies
        Returns the most likely location string or empty string if none found
        """
        location = ""
        potential_locations = []

        # First try element-based location detection (most reliable)
        location_patterns = [
            '//div[contains(@class, "location")]',
            '//span[contains(@class, "location")]',
            '//div[contains(text(), "Location:")]/following-sibling::div',
            '//span[contains(text(), "location:")]/following-sibling::span',
        ]

        for pattern in location_patterns:
            try:
                loc_elem = driver.find_element(By.XPATH, pattern)
                if loc_elem:
                    location = loc_elem.text.strip()
                    if location and self.validate_location(location) > 50:
                        logger.info(f"Found location from element: '{location}'")
                        return location
                    potential_locations.append(
                        (location, 50)
                    )  # Medium confidence for element-based
            except:
                pass

        # Next try text-based pattern matching
        lines = text_content.split("\n")

        # Pattern-based location detection with international format support
        location_patterns = [
            # City, State, Country (US format)
            r"([A-Z][a-zÀ-ÿ]+(?:[\s-][A-Z][a-zÀ-ÿ]+)*),\s*([A-Z]{2}|[A-Za-zÀ-ÿ ]+),\s*([A-Za-zÀ-ÿ ]+)",
            # City, State/Country
            r"([A-Z][a-zÀ-ÿ]+(?:[\s-][A-Z][a-zÀ-ÿ]+)*),\s*([A-Z]{2}|[A-Za-zÀ-ÿ ]+)",
            # City, Country
            r"([A-Z][a-zÀ-ÿ]+(?:[\s-][A-Z][a-zÀ-ÿ]+)*),\s*([A-Za-zÀ-ÿ ]+)",
            # Country (Region) format - common in Asia
            r"([A-Za-zÀ-ÿ ]+)\s*\(([A-Za-zÀ-ÿ ]+)\)",
            # Postal code city format (Europe)
            r"(\d{4,6})\s+([A-Z][a-zÀ-ÿ]+(?:[\s-][A-Z][a-zÀ-ÿ]+)*)",
        ]

        for line in lines:
            # Skip very short lines or lines likely to be the company name (first line)
            if len(line) < 5 or line == lines[0]:
                continue

            # Try each location pattern
            for pattern in location_patterns:
                match = re.search(pattern, line)
                if match:
                    location = match.group(0)
                    confidence = self.validate_location(location)
                    if confidence > 70:  # Higher threshold for pattern matches
                        logger.info(
                            f"Found location from pattern: '{location}' with confidence {confidence}"
                        )
                        return location
                    potential_locations.append((location, confidence))

        # Check against database of known locations
        for line in lines[1:]:  # Skip first line (likely company name)
            confidence = self.validate_location(line)
            if confidence > 60:  # Good confidence level
                location = line.strip()
                logger.info(
                    f"Found location from database match: '{location}' with confidence {confidence}"
                )
                return location
            elif confidence > 30:  # Possible match
                potential_locations.append((line.strip(), confidence))

        # If we have potential locations, pick the one with highest confidence
        if potential_locations:
            potential_locations.sort(key=lambda x: x[1], reverse=True)
            if potential_locations[0][1] > 30:  # Minimum threshold
                return potential_locations[0][0]

        # Fallback: Look for lines that might be just a location
        for line in lines[1:]:  # Skip first line (likely company name)
            # Check if this looks like a standalone location
            # Typically these have commas and aren't very long
            if "," in line and 5 < len(line) < 50:
                confidence = self.validate_location(line)
                if confidence > 30:
                    location = line.strip()
                    logger.info(
                        f"Found potential location: '{location}' with confidence {confidence}"
                    )
                    return location

        # No location found
        return ""

    def fetch_startups(
        self, year=None, track_run=True, headless=True, wait_time=10, limit=None
    ):
        """
        Fetch startups from Y Combinator

        Args:
            year (int, optional): Filter startups by year
            track_run (bool): Whether to track this run in the database
            headless (bool): Whether to run the browser in headless mode
            wait_time (int): How many seconds to wait for content to load
            limit (int, optional): Maximum number of startups to process

        Returns:
            list: List of startup dictionaries
        """
        logger.info(
            f"Starting to scrape YC startups with Selenium for year: {year or 'all'}, limit: {limit or 'none'}"
        )

        # Refresh location data before starting scraping
        self.refresh_location_data()

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
                year, headless=headless, wait_time=wait_time, limit=limit
            )

            # Save each startup to the database
            saved_startups = []
            for raw_startup_data in startups:
                try:
                    # Process the raw data into a standardized format
                    processed_data = self.process_startup_data(raw_startup_data)

                    # Save the processed data to the database
                    startup, is_created = self._save_startup_to_db(processed_data)
                    saved_startups.append(startup)

                    status = "Created" if is_created else "Updated"
                    logger.info(
                        f"{status} startup in database: {processed_data['name']}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to save startup {raw_startup_data.get('name', 'Unknown')}: {e}"
                    )

            # Update stats with total count
            self.stats["total"] = len(startups)
            logger.info(
                f"Saved {len(saved_startups)} startups to database (Added: {self.stats['added']}, Updated: {self.stats['updated']}, Unchanged: {self.stats['unchanged']})"
            )

            # Complete run if tracking enabled
            if track_run and self.current_run:
                complete_scraper_run(self.current_run.id, "success", self.stats, db=db)

            return saved_startups

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

    # private method.
    def _scrape_with_selenium(self, year=None, headless=True, wait_time=10, limit=None):
        """Scrape YC startups using Selenium for browser automation"""
        logger.info("Starting Selenium-based web scraping...")
        all_startups = []
        failed_extractions = []

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
                # Create separate batches for different sessions
                # W = Winter, S = Spring, F = Fall (2024+), X = Summer (2025+)
                batches = [f"W{short_year}", f"S{short_year}"]

                # Add Fall batch for 2024 and later
                if year >= 2024:
                    batches.append(f"F{short_year}")

                # Add Summer batch for 2025 and later
                if year >= 2025:
                    batches.append(f"X{short_year}")

                logger.info(
                    f"Will scrape each batch individually: {', '.join(batches)}"
                )
            else:
                # If no year is provided, scrape the last 5 years
                current_year = datetime.now().year
                years_to_scrape = list(
                    range(current_year - 4, current_year + 1)
                )  # Last 5 years
                logger.info(
                    f"No year specified, scraping last 5 years: {years_to_scrape}"
                )

                for year_to_scrape in years_to_scrape:
                    short_year = str(year_to_scrape)[-2:]
                    year_batches = [f"W{short_year}", f"S{short_year}"]

                    # Add Fall batch for 2024 and later
                    if year_to_scrape >= 2024:
                        year_batches.append(f"F{short_year}")

                    # Add Summer batch for 2025 and later
                    if year_to_scrape >= 2025:
                        year_batches.append(f"X{short_year}")

                    batches.extend(year_batches)

                logger.info(f"Will scrape these batches: {', '.join(batches)}")

            # Process each batch separately
            for batch in batches:
                # Navigate directly with filter URL parameters
                url = self.base_url
                if batch:
                    url = f"{url}?batch={batch}"
                    logger.info(f"Scraping batch: {batch} at URL: {url}")
                else:
                    logger.info(f"Scraping all batches at URL: {url}")

                # Retry mechanism for page load
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        logger.info(f"Navigating to {url} (attempt {retry_count + 1})")
                        driver.get(url)

                        # Wait for the page to load with multiple conditions
                        wait = WebDriverWait(driver, wait_time + 5)
                        wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                        )
                        wait.until(
                            EC.presence_of_element_located(
                                (
                                    By.CSS_SELECTOR,
                                    'a[class*="_company_"], a[href^="/companies/"]',
                                )
                            )
                        )

                        # Allow time for JavaScript to render content
                        time.sleep(wait_time)
                        break
                    except Exception as e:
                        retry_count += 1
                        logger.warning(
                            f"Failed to load page (attempt {retry_count}): {e}"
                        )
                        if retry_count == max_retries:
                            logger.error(
                                f"Failed to load page after {max_retries} attempts"
                            )
                            continue

                # Multiple selectors for company links
                selectors = [
                    'a[class*="_company_"]',
                    'a[href^="/companies/"]',
                    'div[class*="rightCol"] a',
                    'div[class*="company-card"] a',
                    'div[class*="CompanyCard"] a',
                ]

                company_links = []
                for selector in selectors:
                    try:
                        links = driver.find_elements(By.CSS_SELECTOR, selector)
                        if links:
                            company_links.extend(links)
                            logger.info(
                                f"Found {len(links)} companies with selector: {selector}"
                            )
                            break
                    except Exception as e:
                        logger.warning(f"Failed with selector {selector}: {e}")

                if not company_links:
                    logger.error("No company links found with any selector")
                    continue

                # Process each company
                processed_count = 0
                for i, link in enumerate(company_links):
                    try:
                        # Check if we've reached the limit
                        if limit and processed_count >= limit:
                            logger.info(
                                f"Reached limit of {limit} companies, stopping scraping"
                            )
                            break

                        # Extract company data with retry mechanism
                        company_data = self._extract_company_data_with_retry(
                            driver, link, i, len(company_links)
                        )
                        if company_data:
                            all_startups.append(company_data)
                            processed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to process company {i+1}: {e}")
                        failed_extractions.append(
                            {
                                "index": i,
                                "error": str(e),
                                "link": link.get_attribute("href"),
                            }
                        )

                # Check if we've reached the limit after processing this batch
                if limit and len(all_startups) >= limit:
                    logger.info(
                        f"Reached limit of {limit} companies, skipping remaining batches"
                    )
                    break

            # Log failed extractions
            if failed_extractions:
                logger.error(f"Failed to extract {len(failed_extractions)} companies:")
                for failure in failed_extractions:
                    logger.error(
                        f"Company {failure['index'] + 1}: {failure['error']} - {failure['link']}"
                    )

            return all_startups

        except Exception as e:
            logger.error(f"Error in Selenium scraper: {e}")
            logger.error(traceback.format_exc())
            return []

        finally:
            try:
                driver.quit()
                logger.info("Closed Selenium browser")
            except Exception:
                pass

    def _extract_company_data_with_retry(self, driver, link, index, total):
        """Enhanced method to extract company data with dynamic location detection"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Extract text content
                text_content = link.text.strip()
                if not text_content:
                    raise ValueError("Empty text content")

                logger.info(f"\n=== Processing Company {index + 1}/{total} ===")
                logger.info(f"Raw text content: '{text_content}'")

                # First identify location - using both element-based and pattern-based approaches
                location = self._extract_location(driver, text_content)

                # Now extract company name
                lines = text_content.split("\n")
                raw_company_name = lines[0] if lines else ""

                # If we found a location, try to extract company name
                if location:
                    # Verify location is valid with high confidence before using it
                    location_confidence = self.validate_location(location)
                    if location_confidence < 60:  # Higher threshold for acceptance
                        logger.warning(
                            f"Rejecting low-confidence location: '{location}' (score: {location_confidence})"
                        )
                        location = ""  # Reset location if confidence is too low
                    else:
                        # Clean the company name using our dynamic method
                        clean_name = self.clean_company_name(raw_company_name, location)

                        # Verify the cleaning actually did something
                        if clean_name != raw_company_name:
                            logger.info(
                                f"Cleaned company name: '{raw_company_name}' -> '{clean_name}'"
                            )
                            raw_company_name = clean_name
                        else:
                            logger.info(
                                f"No name cleaning needed for: '{raw_company_name}'"
                            )

                # If no location found or low confidence, try again with parsing
                if not location:
                    # If no location found, try to parse company name and location from raw text
                    company, loc = self._try_parse_company_and_location(
                        raw_company_name
                    )
                    if loc and self.validate_location(loc) >= 60:
                        raw_company_name = company
                        location = loc
                        logger.info(
                            f"Parsed company '{company}' and location '{loc}' from raw text"
                        )

                # Log final results after all parsing and cleaning
                logger.info(f"Final company name: '{raw_company_name}'")
                logger.info(f"Final location: '{location}'")

                # Get description (first line that's not the company name or location)
                description = ""
                for line in lines[1:]:
                    # Skip if the line matches the company name or location
                    if (
                        line.strip() == location.strip()
                        or line.strip() == raw_company_name.strip()
                    ):
                        continue
                    if line.strip():
                        description = line.strip()
                        break

                # Extract batch and tags
                batch = ""
                tags = []
                batch_match = re.search(r"([WSFX]\d{2})", text_content)
                if batch_match:
                    batch = batch_match.group(0)

                # Try to extract logo URL
                logo_url = ""
                try:
                    logo_elem = link.find_element(
                        By.CSS_SELECTOR,
                        'img[src*="bookface-images.s3"], img[src*="logo"], img[src*="Logo"]',
                    )
                    if logo_elem:
                        logo_url = logo_elem.get_attribute("src")
                except:
                    pass

                # Create company data structure
                company_data = {
                    "name": raw_company_name.strip(),
                    "description": description.strip(),
                    "batch": batch,
                    "url": link.get_attribute("href") or "",
                    "logo_url": logo_url,
                    "tags": "",
                    "status": "ACTIVE",
                    "team_size": "",
                    "location": location.strip(),
                    "founders": [],
                }

                # Post-processing validation to catch and correct obvious errors
                company_data = self._validate_and_correct_company_data(
                    company_data, text_content
                )

                # Final verification for specific pattern issues
                company_data = self._verify_company_location_separation(company_data)

                # Compare before and after post-processing
                if company_data["name"] != raw_company_name:
                    logger.info(
                        f"Post-processing modified name: '{raw_company_name}' -> '{company_data['name']}'"
                    )

                if company_data["location"] != location:
                    logger.info(
                        f"Post-processing modified location: '{location}' -> '{company_data['location']}'"
                    )

                # Final validation check - name shouldn't be very short or contain location
                if len(company_data["name"]) < 2:
                    logger.warning(
                        f"Final company name is suspiciously short: '{company_data['name']}'"
                    )

                if (
                    company_data["location"]
                    and company_data["location"] in company_data["name"]
                ):
                    logger.warning(
                        f"Final company name still contains location: '{company_data['name']}' contains '{company_data['location']}'"
                    )

                # Verify data completeness
                if not company_data["name"] or not company_data["url"]:
                    raise ValueError("Missing required company data")

                logger.info(f"Final company data: {company_data}")
                return company_data

            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Failed to extract company data (attempt {retry_count}): {e}"
                )
                if retry_count == max_retries:
                    raise
                time.sleep(2)  # Wait before retry

        return None

    def _verify_company_location_separation(self, company_data):
        """Special verification for common patterns where names get attached to locations"""
        name = company_data["name"]
        location = company_data["location"]

        # Nothing to verify if we don't have both name and location
        if not name or not location:
            return company_data

        # Copy the data to avoid direct modification
        verified_data = company_data.copy()

        # Check for department-like text in location field
        if (
            location.upper() == location
            and "," in location
            and len(location.split()) >= 3
        ):
            # Likely a department or title, not a location
            verified_data["location"] = ""
            logger.info(f"Removed likely department name from location: '{location}'")
            return verified_data

        # Fix ALL CAPS company names with international locations (e.g., "STARK BANKSão Paulo")
        if name == name.upper() and any(ord(c) > 127 for c in name):
            # Find transition between ASCII uppercase and accented chars
            for i in range(len(name) - 1):
                if ord(name[i]) < 128 and ord(name[i + 1]) > 127:
                    # Check if we have a clean break point that's not mid-word
                    if i > 0 and len(name[: i + 1].strip()) >= 2:
                        verified_data["name"] = name[: i + 1].strip()

                        # Only set location if we don't already have one
                        if not location:
                            verified_data["location"] = name[i + 1 :].strip()

                        logger.info(
                            f"Split all-caps international name: '{name}' -> '{verified_data['name']}' + '{name[i+1:]}'"
                        )
                        break

        # Pattern 1: CompanyNameCityName - no spaces between company and city
        # Look for common city prefixes in the name without spaces
        for city in self.major_cities:
            if city in name and not f" {city}" in name:
                city_pos = name.find(city)
                if city_pos > 0:
                    verified_data["name"] = name[:city_pos].strip()
                    logger.info(
                        f"Split city from name: '{name}' -> '{verified_data['name']}' + '{city}'"
                    )
                    break

        # Pattern 1.5: Enhanced city detection - find embedded city names at word boundaries
        # This addresses cases like "OchreBioOxford" or "LivingCarbonCharleston"
        for city in self.major_cities:
            # Skip short city names to avoid false positives
            if len(city) <= 3:
                continue

            # Create pattern to find city names with no space before them
            city_pattern = r"([A-Za-z]+)(" + re.escape(city) + r")"
            match = re.search(city_pattern, name)
            if match and match.group(1) != "":
                # Make sure it's not just a partial match (e.g., "Manchester" in "Romanchester")
                prefix = match.group(1)
                if (
                    len(prefix) >= 2 and not prefix[-1].islower()
                ):  # Last char should be uppercase or non-alpha
                    verified_data["name"] = prefix.strip()
                    if not location:
                        verified_data["location"] = city
                    logger.info(
                        f"Split embedded city from name: '{name}' -> '{verified_data['name']}' + '{city}'"
                    )
                    break

        # Pattern 2: CompanyAISanFrancisco - common patterns seen in logs
        ai_city_pattern = r"([A-Za-z]+)AI([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)"
        match = re.search(ai_city_pattern, name)
        if match:
            verified_data["name"] = match.group(1) + " AI"
            logger.info(f"Split AI-city pattern: '{name}' -> '{verified_data['name']}'")

        # Pattern 3: Multi-word company names with concatenated locations
        # This handles cases like "Nomic BioMontreal" where there's a space in the company name
        # but not between company and location
        multi_word_pattern = r"([A-Za-z]+\s+[A-Za-z]+)([A-Z][a-z]+)"
        match = re.search(multi_word_pattern, name)
        if match:
            company_part = match.group(1)
            location_part = match.group(2)

            # Verify the location part matches a known location
            for city in self.major_cities:
                if city.startswith(location_part) or location_part == city:
                    verified_data["name"] = company_part.strip()
                    if not location:
                        verified_data["location"] = city
                    logger.info(
                        f"Split multi-word company from location: '{name}' -> '{company_part}' + '{city}'"
                    )
                    break

        # Pattern 4: International city names concatenated: CompanyNameSãoPaulo
        # Already handled by international character boundary detection, but check once more
        for city in ["São Paulo", "México", "Bogotá", "Montréal"]:
            normalized_city = unicodedata.normalize("NFD", city)
            normalized_name = unicodedata.normalize("NFD", name)

            if normalized_city in normalized_name:
                city_pos = normalized_name.find(normalized_city)
                if city_pos > 0:
                    verified_data["name"] = name[:city_pos].strip()
                    logger.info(
                        f"Split international city: '{name}' -> '{verified_data['name']}' + '{city}'"
                    )
                    break

        # Pattern 5: Handle single city name at the end (e.g., "CompanyNameTokyo")
        for city in self.major_cities:
            city_pattern = r"(\w+)(" + re.escape(city) + r")$"
            match = re.search(city_pattern, name, re.IGNORECASE)
            if match and match.group(1) != "":
                verified_data["name"] = match.group(1).strip()
                logger.info(
                    f"Split single city from name: '{name}' -> '{verified_data['name']}' + '{city}'"
                )
                break

        # Pattern 6: Common locations that might be appended (e.g., "CompanyUSA")
        common_regions = ["USA", "EU", "UK", "UAE", "HK"]
        for region in common_regions:
            region_pattern = r"(\w+)(" + re.escape(region) + r")$"
            match = re.search(region_pattern, name)
            if match and match.group(1) != "":
                verified_data["name"] = match.group(1).strip()
                if not location:
                    verified_data["location"] = region
                logger.info(
                    f"Split region code from name: '{name}' -> '{verified_data['name']}' + '{region}'"
                )
                break

        # Pattern 7: Bio/Health/Tech company name concatenated with location
        # This specifically handles common patterns like: "Ochre BioOxford" or "YassirAlgeria"
        tech_suffixes = ["Bio", "Health", "Tech", "AI", "Labs", "Med"]
        for suffix in tech_suffixes:
            # Look for patterns like CompanyNameBioLocation
            suffix_pattern = r"([A-Za-z]+\s*)(" + re.escape(suffix) + r")([A-Z][a-z]+)"
            match = re.search(suffix_pattern, name)
            if match:
                company_part = match.group(1) + match.group(2)
                location_part = match.group(3)

                # Verify location part against known cities
                is_known_location = False
                for city in self.major_cities:
                    if city.startswith(location_part) or location_part in city:
                        is_known_location = True
                        verified_data["name"] = company_part.strip()
                        if not location:
                            verified_data["location"] = city
                        logger.info(
                            f"Split tech suffix with location: '{name}' -> '{company_part}' + '{city}'"
                        )
                        break

                if is_known_location:
                    break

        # Final sanity check - if the company name contains a comma, it might still have location attached
        if "," in verified_data["name"] and not verified_data["name"].startswith('"'):
            parts = verified_data["name"].split(",", 1)
            if len(parts) == 2 and len(parts[0]) >= 2:
                verified_data["name"] = parts[0].strip()
                logger.info(f"Split at comma: '{name}' -> '{verified_data['name']}'")

        return verified_data

    def _validate_and_correct_company_data(self, company_data, raw_text):
        """
        Post-processing validation to catch and correct obvious errors in extracted data
        """
        # Make a copy of the data to avoid modifying the original directly
        validated_data = company_data.copy()

        # 1. Validate company name
        name = validated_data["name"]
        location = validated_data["location"]
        description = validated_data["description"]

        # Check for very short company names (likely incomplete extraction)
        if len(name) < 3 and len(raw_text) > 10:
            # Try to get a better name from the first line of raw text
            lines = raw_text.split("\n")
            if lines and len(lines[0]) > len(name):
                # Use the first line, but remove any known location
                better_name = lines[0]
                if location and location in better_name:
                    better_name = better_name.replace(location, "").strip()
                validated_data["name"] = better_name
                logger.info(
                    f"Corrected short company name from '{name}' to '{better_name}'"
                )

        # 2. Check if company name contains HTML or markdown - common scraping artifacts
        if "<" in name and ">" in name or "[" in name and "]" in name:
            # Try to extract text without HTML/markdown
            cleaned_name = re.sub(r"<[^<]+?>", "", name)  # Remove HTML tags
            cleaned_name = re.sub(r"\[.*?\]", "", cleaned_name)  # Remove markdown
            if cleaned_name.strip():
                validated_data["name"] = cleaned_name.strip()
                logger.info(
                    f"Removed HTML/markdown from company name: '{name}' -> '{cleaned_name}'"
                )

        # 3. Validate location with higher confidence threshold
        if location:
            # Check if the location might actually be part of the description
            location_confidence = self.validate_location(location)

            if location_confidence < 60:  # Higher threshold for accepting locations
                # Low confidence location might be a description fragment
                validated_data["location"] = ""
                logger.info(
                    f"Removed low-confidence location '{location}' (score: {location_confidence})"
                )

                # If it looks like a description, add it to the description field if empty
                if self._is_description_not_location(location) and not description:
                    validated_data["description"] = location
                    logger.info(f"Moved location text to description: '{location}'")

        # 4. Description vs Location confusion check
        if description and location:
            # If description is very short and location is long, they might be swapped
            if len(description) < 15 and len(location) > 30:
                desc_confidence = self.validate_location(description)
                loc_confidence = self.validate_location(location)

                if desc_confidence > loc_confidence:
                    # Swap them
                    validated_data["description"] = location
                    validated_data["location"] = description
                    logger.info(
                        f"Swapped description and location (based on confidence scores)"
                    )

        # 5. Check for location artifacts in company name (camelCase with location suffixes)
        if name and location:
            # Check for company names that end with partial location strings
            for word in location.split():
                if len(word) > 3 and name.endswith(word):
                    corrected_name = name[: -len(word)].strip()
                    if len(corrected_name) >= 3:
                        validated_data["name"] = corrected_name
                        logger.info(
                            f"Removed location suffix from company name: '{name}' -> '{corrected_name}'"
                        )
                        break

        # 6. Handle international character boundaries - specific focus on cases like "STARK BANKSão Paulo"
        if name:
            # Look for transitions between ASCII and non-ASCII characters without spaces
            int_matches = list(re.finditer(r"([A-Z][A-Z]+)([À-ÿ][a-zÀ-ÿ]+)", name))

            if int_matches:
                for match in int_matches:
                    potential_company = match.group(1)
                    potential_location = name[match.start(2) :]

                    # Check if potential location is valid
                    loc_confidence = self.validate_location(potential_location)

                    # If we have high confidence or location contains accented characters
                    if loc_confidence > 30 or any(
                        ord(c) > 127 for c in potential_location
                    ):
                        validated_data["name"] = potential_company

                        # Only update location if we found a better one
                        if not location or loc_confidence > self.validate_location(
                            location
                        ):
                            validated_data["location"] = potential_location

                        logger.info(
                            f"Fixed international name boundary: '{name}' -> '{potential_company}' + '{potential_location}'"
                        )
                        break

            # Also check for cases where uppercase followed by accented
            elif not int_matches and any(ord(c) > 127 for c in name):
                ascii_pattern = r"([A-Za-z])([À-ÿ])"
                match = re.search(ascii_pattern, name)
                if match:
                    split_point = match.start() + 1
                    corrected_name = name[:split_point].strip()
                    potential_location = name[split_point:].strip()

                    # Only apply if corrected name is reasonable and we have sufficient confidence
                    if (
                        len(corrected_name) >= 3
                        and self.validate_location(potential_location) > 30
                    ):
                        validated_data["name"] = corrected_name
                        if not location:
                            validated_data["location"] = potential_location
                        logger.info(
                            f"Split international name: '{name}' -> '{corrected_name}' + '{potential_location}'"
                        )

        # 7. Special handling for Spanish/Portuguese company names with locations
        for city in ["São Paulo", "México City", "Bogotá", "CDMX", "Rio de Janeiro"]:
            if name and city in name:
                # Case-insensitive search to catch variations
                pattern = re.compile(re.escape(city), re.IGNORECASE)
                match = pattern.search(name)
                if match:
                    split_point = match.start()
                    if split_point > 0:
                        corrected_name = name[:split_point].strip()
                        if len(corrected_name) >= 3:
                            validated_data["name"] = corrected_name
                            if not location:
                                validated_data["location"] = city
                            logger.info(
                                f"Split Latin American location: '{name}' -> '{corrected_name}' + '{city}'"
                            )

        # 8. Remove common prefixes from description if they appear to be formatting artifacts
        if description:
            common_prefixes = ["Description:", "About:", "•", "-", ">"]
            for prefix in common_prefixes:
                if description.startswith(prefix):
                    validated_data["description"] = description[len(prefix) :].strip()
                    logger.info(f"Removed prefix from description: '{prefix}'")
                    break

        return validated_data

    def _try_parse_company_and_location(self, text):
        """
        Attempt to parse company name and location from a single text string
        Returns tuple (company_name, location) or (text, "") if no location found
        """
        if not text or len(text) < 5:
            return text, ""

        # First check if text is likely a description, not a company+location
        description_indicators = [
            "platform",
            "software",
            "marketplace",
            "solution",
            "app",
            "api",
            "service",
            "for",
            "that",
            "helps",
        ]

        lower_text = text.lower()
        if sum(1 for word in description_indicators if word in lower_text.split()) >= 2:
            # Likely a description, not a company+location
            return text, ""

        # Try to identify camelcase boundaries (e.g., "CompanyNameSanFrancisco")
        camel_case_pattern = r"([a-z])([A-Z])"
        matches = list(re.finditer(camel_case_pattern, text))

        if matches:
            for match in reversed(matches):  # Start from the end to find location first
                split_point = match.start() + 1
                potential_company = text[:split_point]
                potential_location = text[split_point:]

                # Validate the potential location with confidence scoring
                confidence = self.validate_location(potential_location)

                # Check if the potential location is likely to be a real location
                if confidence > 40:
                    return potential_company, potential_location

        # Handle international characters at word boundaries
        # Look for transitions from lowercase to uppercase with accented chars
        international_pattern = r"([a-z])([À-ÿ][A-Z])"
        matches = list(re.finditer(international_pattern, text))

        if matches:
            for match in reversed(matches):
                split_point = match.start() + 1
                potential_company = text[:split_point]
                potential_location = text[split_point:]

                confidence = self.validate_location(potential_location)
                if confidence > 40:
                    return potential_company, potential_location

        # Try comma-based splitting
        if "," in text:
            parts = text.split(",", 1)
            if len(parts) == 2 and len(parts[0]) >= 3:
                # Check if second part looks like a location
                confidence = self.validate_location(parts[1])
                if confidence > 40:
                    return parts[0].strip(), parts[1].strip()

        # Try common location word identification
        for prefix in self.common_location_prefixes:
            if prefix in text and not text.startswith(prefix):
                prefix_pos = text.find(prefix)
                if prefix_pos > 0:
                    # Check if there's a word boundary before the prefix
                    if not text[prefix_pos - 1].isalnum():
                        potential_company = text[:prefix_pos].strip()
                        potential_location = text[prefix_pos:].strip()
                        if (
                            len(potential_company) >= 2
                            and self.validate_location(potential_location) > 30
                        ):
                            return potential_company, potential_location

        # No location found in text
        return text, ""

    def clean_company_name(self, name, location):
        """
        Enhanced method to clean company name by properly separating from location
        Uses dynamic location data and validation to ensure proper separation
        """
        if not name or not location:
            return name.strip() if name else ""

        # Special case for very long names with location at the end
        if len(name) > 50 and location in name:
            # Directly replace the location without any additional checks
            return name.replace(location, "").strip()

        # Normalize text for better handling of international characters
        normalized_name = unicodedata.normalize("NFD", name)
        normalized_location = unicodedata.normalize("NFD", location)

        # Clean the location to ensure it's actually a location
        location_confidence = self.validate_location(location)
        if location_confidence < 30:
            logger.warning(
                f"Low confidence location: '{location}' (score: {location_confidence})"
            )
            # Return just the name if location confidence is too low
            if location_confidence < 20:
                return name.strip()

        # Refresh location data if it's been a while
        if not self.known_locations:
            self.refresh_location_data()

        # Special case for San Francisco being misplaced in the middle of the name
        if "San Francisco" in name and not name.endswith("San Francisco"):
            sf_pos = name.find("San Francisco")
            if sf_pos > 0:
                return name[:sf_pos].strip()

        # Check for international cases like "STARK BANKSão Paulo"
        # Look for transitions from ASCII to accented characters without spaces
        int_match = re.search(r"([A-Za-z])([À-ÿ])", name)
        if int_match:
            split_point = int_match.start() + 1
            potential_company = name[:split_point]
            potential_location = name[split_point:]

            # If location contains our actual location or matches better patterns
            if (
                location in potential_location
                or potential_location in location
                or self.validate_location(potential_location) > 40
            ):
                if len(potential_company) >= 2:
                    logger.info(
                        f"Split international name boundary: {name} -> {potential_company}"
                    )
                    return potential_company

        # First try the simplest case - direct replacement of location from end of name
        name_without_location = re.sub(r"[,\s]*" + re.escape(location) + r"$", "", name)
        if name_without_location != name and len(name_without_location.strip()) >= 2:
            return name_without_location.strip()

        # Special case for concatenated international character locations
        # Look for abrupt character set changes (e.g. "STARKBANKSão Paulo")
        matches = list(re.finditer(r"([a-zA-Z])([À-ÿ])", name))
        if matches:
            for match in reversed(matches):  # Start from the end for greedy matching
                split_point = match.start() + 1
                potential_company = name[:split_point]
                potential_location = name[split_point:]

                # Check if potential_location contains our known location
                if location in potential_location or potential_location in location:
                    if len(potential_company) >= 3:  # Reasonable company name length
                        return potential_company.strip()

        # Special case for multi-word company names followed by location
        words = name.split()
        if len(words) >= 3:  # At least 2 words for company + start of location
            for i in range(1, len(words)):
                potential_company = " ".join(words[:i])
                potential_location = " ".join(words[i:])

                # Only accept if this is a clear location and not description-like
                confidence = self.validate_location(potential_location)

                # Check if potential location contains the actual location
                # or if it's a known location in our database with good confidence
                if (
                    location in potential_location or potential_location in location
                ) and confidence > 40:
                    if len(potential_company) >= 3:  # Reasonable company name length
                        return potential_company.strip()

        # Handle non-ASCII characters in locations
        # Try finding the location in the normalized name
        if normalized_location in normalized_name:
            # Get the position of location in normalized name
            loc_start = normalized_name.find(normalized_location)
            if loc_start > 0:
                # Return the part before location in the original name
                return name[:loc_start].strip()

        # Handle missing spaces between company name and location
        # Look for CamelCase patterns or sudden changes in character types

        # 1. Look for patterns where lowercase is followed by uppercase (CamelCase boundary)
        camel_case_pattern = r"([a-z])([A-Z])"
        matches = list(re.finditer(camel_case_pattern, name))
        if matches:
            for match in reversed(matches):  # Check from the end first
                split_point = match.start() + 1  # Position after the lowercase letter
                company_part = name[:split_point]
                location_part = name[split_point:]

                # Check if split makes sense (location part contains the location or is a known location)
                # with validation to avoid false positives
                confidence = self.validate_location(location_part)

                if (
                    (location in location_part or location_part in location)
                    or confidence > 50
                ) and len(company_part) >= 2:
                    return company_part

        # 2. Multi-word company names with location partially matching the end
        # Look for partial location words at the end of the name
        location_words = location.split()
        if location_words:
            first_loc_word = location_words[0]
            # Look for the first location word in the name
            loc_word_pos = name.find(first_loc_word)
            if loc_word_pos > 0:
                # Make sure it's not part of the company name by checking if it's a standalone word
                if (
                    (loc_word_pos == 0 or not name[loc_word_pos - 1].isalnum())
                    and (
                        loc_word_pos + len(first_loc_word) >= len(name)
                        or not name[loc_word_pos + len(first_loc_word)].isalnum()
                    )
                    and self.validate_location(name[loc_word_pos:]) > 40
                ):
                    return name[:loc_word_pos].strip()

        # 3. Check for company names with locations embedded in them
        # Use database-derived location prefixes instead of hardcoded list
        for prefix in self.common_location_prefixes:
            if prefix in name and prefix not in location:
                # Skip if it's part of a legitimate company name at the beginning
                if name.startswith(prefix):
                    continue

                prefix_pos = name.find(prefix)
                if prefix_pos > 0:
                    # Check if there's a word boundary before the prefix
                    if not name[prefix_pos - 1].isalnum():
                        potential_company = name[:prefix_pos].strip()
                        potential_location = name[prefix_pos:]
                        if (
                            len(potential_company) >= 3
                            and self.validate_location(potential_location) > 30
                        ):  # Reasonable company name length
                            return potential_company

        # 4. Try to find incomplete location extraction (e.g., "italsIrvine")
        # Check if part of the location is concatenated to the company name
        for i in range(
            1, min(len(location), 5)
        ):  # Check up to first 4 chars of location
            location_start = location[:i]
            location_rest = location[i:]

            if name.endswith(location_start):
                # The name ends with the start of the location
                return name[: -len(location_start)].strip()

        # Handle cases where company includes location identity terms
        if location in name and name.startswith(location):
            rest = name[len(location) :].strip()
            if rest and location in rest:
                # If location appears at start and elsewhere, keep only the start part
                loc_pos = rest.find(location)
                if loc_pos > 0:
                    return location + " " + rest[:loc_pos].strip()

        # Last resort - if name contains location with other text
        # Try to identify a natural boundary by looking for common separators
        for sep in [",", "-", "|", ":", ";", "•"]:
            if sep in name:
                parts = name.split(sep, 1)
                if location in parts[1]:
                    return parts[0].strip()
                elif location in parts[0]:
                    return parts[1].strip()

        # If we couldn't separate, just return the original name
        return name.strip()

    def process_startup_data(self, raw_data):
        """
        Process raw startup data into a standardized format

        Args:
            raw_data: Raw data from the source

        Returns:
            dict: Processed startup data in standardized format
        """
        # Extract year from batch (e.g., "W24" -> 2024)
        batch = raw_data.get("batch", "")
        year_founded = (
            self._extract_year_from_batch(batch) if batch else datetime.now().year
        )

        # Process location
        location = raw_data.get("location", "")

        # Clean company name by removing location if it's appended
        name = raw_data.get("name", "")
        if location:
            # Use our improved clean_company_name method instead of simple replacement
            name = self.clean_company_name(name, location)

        # Convert tags from list to comma-separated string if needed
        tags = raw_data.get("tags", [])
        if isinstance(tags, list):
            tags = ",".join(tags) if tags else ""

        # Convert team size to integer if possible
        team_size = raw_data.get("team_size", "")
        if team_size and isinstance(team_size, str):
            try:
                team_size = int(team_size)
            except ValueError:
                team_size = None

        # Build standardized startup data
        startup_data = {
            "name": name,
            "description": raw_data.get("description", ""),
            "year_founded": year_founded,
            "url": raw_data.get("url", ""),
            "logo_url": raw_data.get("logo_url", ""),
            "source": "YC",
            "batch": batch,
            "status": raw_data.get("status", "ACTIVE"),
            "location": location,
            "tags": tags,
            "team_size": team_size,
            "founders": raw_data.get("founders", []),
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

        # Basic validation for year_founded
        if startup_data.get("year_founded") is None:
            batch = startup_data.get("batch", "")
            startup_data["year_founded"] = (
                self._extract_year_from_batch(batch) if batch else datetime.now().year
            )

            batch = startup_data.get("batch", "")
            startup_data["year_founded"] = (
                self._extract_year_from_batch(batch) if batch else datetime.now().year
            )

        # Debug print raw data
        print("\n=== Debug: Raw Startup Data ===")
        print(f"Name: {startup_data.get('name')}")
        print(f"Description: {startup_data.get('description')}")
        print(f"Location: {startup_data.get('location')}")
        print(f"Team Size: {startup_data.get('team_size')}")
        print(f"Tags: {startup_data.get('tags')}")
        print(f"Status: {startup_data.get('status')}")
        print(f"Batch: {startup_data.get('batch')}")
        print(f"Year Founded: {startup_data.get('year_founded')}")
        print(f"URL: {startup_data.get('url')}")
        print(f"Logo URL: {startup_data.get('logo_url')}")
        print("=============================\n")

        # Check if startup already exists (by name and batch/year)
        existing_startup = Startup.query.filter_by(
            name=startup_data["name"], batch=startup_data.get("batch")
        ).first()

        is_updated = False
        is_created = False

        if existing_startup:
            # Debug print existing startup data
            print("\n=== Debug: Existing Startup Data ===")
            print(f"Existing Name: {existing_startup.name}")
            print(f"Existing Team Size: {existing_startup.team_size}")
            print(f"Existing Founders Count: {len(existing_startup.founders)}")
            print(f"Existing Tags: {existing_startup.tags}")
            print("=============================\n")

            # Make sure year_founded is set for existing startups
            if startup_data.get("year_founded") is None:
                batch = startup_data.get("batch", "")
                startup_data["year_founded"] = (
                    self._extract_year_from_batch(batch)
                    if batch
                    else datetime.now().year
                )

            # Check if any data has changed
            data_changed = False
            for key, value in startup_data.items():
                current_value = getattr(existing_startup, key)
                if current_value != value:
                    print(f"\n=== Debug: Data Change Detected ===")
                    print(f"Field: {key}")
                    print(f"Old Value: {current_value}")
                    print(f"New Value: {value}")
                    print("=============================\n")
                    setattr(existing_startup, key, value)
                    data_changed = True

            if data_changed:
                print(f"Updating existing startup: {startup_data['name']}")
                is_updated = True
            else:
                print(f"Startup unchanged: {startup_data['name']}")

            startup = existing_startup
        else:
            print(f"Creating new startup: {startup_data['name']}")
            # Create new startup
            if startup_data.get("year_founded") is None:
                # Extract year from batch
                batch = startup_data.get("batch", "")
                startup_data["year_founded"] = (
                    self._extract_year_from_batch(batch)
                    if batch
                    else datetime.now().year
                )

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
                    current_value = getattr(existing_founder, key)
                    if current_value != value:
                        print(f"\n=== Debug: Founder Data Change Detected ===")
                        print(f"Founder: {founder_data['name']}")
                        print(f"Field: {key}")
                        print(f"Old Value: {current_value}")
                        print(f"New Value: {value}")
                        print("=============================\n")
                        setattr(existing_founder, key, value)
                        founder_changed = True

                if founder_changed and not is_updated:
                    is_updated = (
                        True  # Mark startup as updated if only founder data changed
                    )
            else:
                # Create new founder
                print(f"\n=== Debug: Creating New Founder ===")
                print(f"Founder: {founder_data['name']}")
                print(f"Title: {founder_data.get('title')}")
                print(f"Role Type: {founder_data.get('role_type')}")
                print("=============================\n")

                new_founder = Founder(**founder_data)
                new_founder.startup_id = startup.id
                db.session.add(new_founder)
                if not is_updated and not is_created:
                    is_updated = True  # Mark as updated if we're adding a new founder

        # Debug print before commit
        print("\n=== Debug: Before Database Commit ===")
        print(f"Startup: {startup.name}")
        print(f"Team Size: {startup.team_size}")
        print(f"Founders Count: {len(startup.founders)}")
        print(f"Tags: {startup.tags}")
        print("=============================\n")

        db.session.commit()

        # Update statistics based on outcome
        if is_created:
            self.stats["added"] += 1
        elif is_updated:
            self.stats["updated"] += 1
        else:
            self.stats["unchanged"] += 1

        return startup, is_created

    def _extract_year_from_batch(self, batch):
        """
        Extract year from batch string (e.g., "W24" -> 2024, "S20" -> 2020, "F24" -> 2024, "X25" -> 2025)

        Args:
            batch (str): Batch string like "W24", "S20", "F24", or "X25"

        Returns:
            int: Full year (e.g., 2024, 2020), or current year if not found
        """
        if not batch or len(batch) < 3:
            return datetime.now().year  # Default to current year

        try:
            # Extract the numeric part
            year_part = batch[-2:]  # Get the last two chars
            if not year_part.isdigit():
                return datetime.now().year

            # Validate the batch prefix is one of the known types
            prefix = batch[0]
            if prefix not in ["W", "S", "F", "X"]:
                logger.warning(
                    f"Unknown batch prefix in '{batch}', defaulting to current year"
                )
                return datetime.now().year

            # Convert to 4-digit year (20XX for batch strings in 2000s)
            year = int(f"20{year_part}")
            return year
        except (ValueError, IndexError):
            # If any errors, return current year
            return datetime.now().year
