import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
import json
from datetime import datetime

from app.scrapers.base_scraper import BaseScraper
from app.models.startup import Startup, Founder
from app.models.db import db
from app.utils.scraper_utils import create_scraper_run, complete_scraper_run

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class YCombinatorScraper(BaseScraper):
    """Y Combinator startup data scraper"""

    def __init__(self):
        super().__init__()
        self.source_name = "YC"
        self.base_url = "https://www.ycombinator.com/companies"
        self.graphql_url = "https://api.ycombinator.com/v1/companies"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://www.ycombinator.com",
            "Referer": "https://www.ycombinator.com/companies",
        }
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
        logger.info(f"Starting to scrape YC startups for year: {year or 'all'}")

        # Create scraper run record if tracking enabled
        if track_run:
            try:
                self.current_run = create_scraper_run(self.source_name, db)
                logger.info(f"Created scraper run #{self.current_run.id}")
            except Exception as e:
                logger.error(f"Failed to create scraper run record: {e}")
                self.current_run = None

        try:
            # Get sample data for YC companies
            # In a production environment, this would be replaced with actual scraping
            # using Selenium or another robust approach
            startups = self._get_sample_data(year)

            # Complete run if tracking enabled
            if track_run and self.current_run:
                complete_scraper_run(self.current_run.id, "success", self.stats, db=db)

            return startups

        except Exception as e:
            logger.error(f"Error fetching YC startups: {e}")

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

    def _fetch_from_website(self, year=None):
        """Fetch data by scraping YC's website using the public company directory"""
        logger.info(
            "This method uses HTML scraping which can be brittle if YC changes their website structure"
        )
        logger.info("Falling back to sample data mode since YC often blocks scraping")

        # Instead of risking blocked requests or broken scrapers, let's use the sample data for now
        # The ideal solution would be to implement Selenium to browse the site like a human
        return self._get_sample_data(year)

        # NOTE: For a production-ready solution, consider using Selenium with the following approach:
        # 1. Launch a headless browser
        # 2. Navigate to https://www.ycombinator.com/companies
        # 3. If year is provided, use the batch filter dropdown
        # 4. Wait for the company cards to load
        # 5. Scrape data from each card
        # 6. Click "Load More" or pagination controls
        # 7. Repeat steps 4-6 until all companies are scraped

    def _extract_company_data(self, card):
        """
        Extract company data from a company card element

        Args:
            card: BeautifulSoup element representing a company card

        Returns:
            dict: Extracted company data
        """
        try:
            # These selectors will need to be adjusted based on YC's actual HTML structure
            name_elem = card.select_one(".company-name") or card.select_one("h3")
            desc_elem = card.select_one(".company-description") or card.select_one("p")

            # Extract basic info
            company_data = {
                "name": name_elem.text.strip() if name_elem else "",
                "description": desc_elem.text.strip() if desc_elem else "",
                "batch": "",
                "url": "",
                "logoUrl": "",
                "tags": [],
                "status": "ACTIVE",  # Default status
                "teamSize": "",
                "location": "",
                "founders": [],
            }

            # Extract URL
            link_elem = card.select_one("a.company-link") or card.select_one(
                'a[href*="//"]'
            )
            if link_elem and link_elem.has_attr("href"):
                company_data["url"] = link_elem["href"]

            # Extract logo URL
            logo_elem = card.select_one("img.company-logo") or card.select_one("img")
            if logo_elem and logo_elem.has_attr("src"):
                company_data["logoUrl"] = logo_elem["src"]

            # Extract batch
            batch_elem = card.select_one(".company-batch") or card.select_one(
                'span[data-testid="batch"]'
            )
            if batch_elem:
                company_data["batch"] = batch_elem.text.strip()

            # Extract tags/industries
            tag_elems = card.select(".company-tag") or card.select("span.tag")
            if tag_elems:
                company_data["tags"] = [tag.text.strip() for tag in tag_elems]

            # Extract location
            location_elem = card.select_one(".company-location") or card.select_one(
                'span[data-testid="location"]'
            )
            if location_elem:
                company_data["location"] = location_elem.text.strip()

            # Check if there are founder details in the card
            founder_elems = card.select(".founder-item") or card.select("div.founder")
            founders = []

            for founder_elem in founder_elems:
                founder_name_elem = founder_elem.select_one(
                    ".founder-name"
                ) or founder_elem.select_one("h4")
                founder_title_elem = founder_elem.select_one(
                    ".founder-title"
                ) or founder_elem.select_one("p")

                founder = {
                    "name": founder_name_elem.text.strip() if founder_name_elem else "",
                    "title": (
                        founder_title_elem.text.strip() if founder_title_elem else ""
                    ),
                    "linkedinUrl": "",
                    "twitterUrl": "",
                }

                # Try to extract social links
                linkedin_elem = founder_elem.select_one('a[href*="linkedin.com"]')
                if linkedin_elem and linkedin_elem.has_attr("href"):
                    founder["linkedinUrl"] = linkedin_elem["href"]

                twitter_elem = founder_elem.select_one('a[href*="twitter.com"]')
                if twitter_elem and twitter_elem.has_attr("href"):
                    founder["twitterUrl"] = twitter_elem["href"]

                founders.append(founder)

            company_data["founders"] = founders

            # If we don't have basic data, skip this card
            if not company_data["name"]:
                return None

            return company_data

        except Exception as e:
            logger.error(f"Error extracting data from card: {e}")
            return None

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

        # Process industry tags
        tags = raw_data.get("tags", []) or raw_data.get("industryTags", [])
        if tags:
            tags_str = ", ".join(tags)
        else:
            tags_str = None

        # Create standardized startup data
        startup_data = {
            "name": raw_data.get("name", ""),
            "description": raw_data.get("description", ""),
            "year_founded": year,
            "url": raw_data.get("url", "") or raw_data.get("website", ""),
            "logo_url": raw_data.get("logoUrl", "") or raw_data.get("logo", ""),
            "source": self.source_name,
            "industry": tags[0] if tags else None,  # Use first tag as primary industry
            "batch": batch,
            "status": (raw_data.get("status", "") or "active").lower(),
            "location": raw_data.get("location", ""),
            "tags": tags_str,
            "team_size": raw_data.get("teamSize", 0) or raw_data.get("team_size", 0),
        }

        # Process founders
        founders_data = []
        founders_list = raw_data.get("founders", []) or []
        for founder in founders_list:
            founder_data = {
                "name": founder.get("name", ""),
                "title": founder.get("title", ""),
                "linkedin_url": founder.get("linkedinUrl", "")
                or founder.get("linkedin", ""),
                "twitter_url": founder.get("twitterUrl", "")
                or founder.get("twitter", ""),
            }
            founders_data.append(founder_data)

        # Add founders to startup data
        startup_data["founders"] = founders_data

        return startup_data

    def _save_startup_to_db(self, startup_data):
        """
        Save startup data to database, tracking if it's new or updated

        Args:
            startup_data (dict): Processed startup data

        Returns:
            tuple: (Startup object, bool indicating if created)
        """
        # Extract founders info
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

        # Process founders
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

    def _get_sample_data(self, year=None):
        """Return sample data for testing purposes"""
        # Sample data with well-known YC companies from various years
        sample_startups = [
            # 2009 Cohort
            {
                "id": "240",
                "name": "Stripe",
                "description": "Economic infrastructure for the internet.",
                "batch": "S09",
                "url": "http://stripe.com",
                "logoUrl": "https://bookface-images.s3.amazonaws.com/logos/85f5d47c3bb6951e8773cf6046491f3a7bcf9b6a.png",
                "industryTags": ["Fintech", "Banking as a Service", "SaaS"],
                "status": "ACTIVE",
                "teamSize": "7000+",
                "location": "San Francisco",
                "founders": [
                    {
                        "name": "John Collison",
                        "title": "Co-founder",
                        "linkedinUrl": "https://www.linkedin.com/in/jcollison/",
                        "twitterUrl": "https://twitter.com/collision",
                    },
                    {
                        "name": "Patrick Collison",
                        "title": "Co-founder, CEO",
                        "linkedinUrl": "https://www.linkedin.com/in/patrickcollison/",
                        "twitterUrl": "https://twitter.com/patrickc",
                    },
                ],
            },
            {
                "id": "271",
                "name": "Airbnb",
                "description": "Book accommodations around the world.",
                "batch": "W09",
                "url": "http://airbnb.com",
                "logoUrl": "https://bookface-images.s3.amazonaws.com/logos/180f55865efc30c4ef7e5f083b8065dc714af28c.png",
                "industryTags": ["Travel", "Marketplace"],
                "status": "PUBLIC",
                "teamSize": "6000+",
                "location": "San Francisco",
                "founders": [
                    {
                        "name": "Brian Chesky",
                        "title": "Co-founder, CEO",
                        "linkedinUrl": "https://www.linkedin.com/in/brianchesky/",
                        "twitterUrl": "https://twitter.com/bchesky",
                    },
                    {
                        "name": "Joe Gebbia",
                        "title": "Co-founder, CPO",
                        "linkedinUrl": "https://www.linkedin.com/in/joegebbia/",
                        "twitterUrl": "https://twitter.com/jgebbia",
                    },
                    {
                        "name": "Nathan Blecharczyk",
                        "title": "Co-founder, CSO",
                        "linkedinUrl": "https://www.linkedin.com/in/nathanblecharczyk/",
                        "twitterUrl": "",
                    },
                ],
            },
            # 2012 Cohort
            {
                "id": "439",
                "name": "Coinbase",
                "description": "Buy, sell, and manage cryptocurrencies.",
                "batch": "S12",
                "url": "https://www.coinbase.com",
                "logoUrl": "https://bookface-images.s3.amazonaws.com/logos/coinbase-logo.png",
                "industryTags": ["Crypto", "Fintech", "Web3"],
                "status": "PUBLIC",
                "teamSize": "3000+",
                "location": "Remote-first",
                "founders": [
                    {
                        "name": "Brian Armstrong",
                        "title": "Co-founder, CEO",
                        "linkedinUrl": "https://www.linkedin.com/in/barmstrong/",
                        "twitterUrl": "https://twitter.com/brian_armstrong",
                    },
                    {
                        "name": "Fred Ehrsam",
                        "title": "Co-founder",
                        "linkedinUrl": "https://www.linkedin.com/in/fredehrsam/",
                        "twitterUrl": "https://twitter.com/fehrsam",
                    },
                ],
            },
            # 2013 Cohort
            {
                "id": "531",
                "name": "DoorDash",
                "description": "Restaurant delivery.",
                "batch": "S13",
                "url": "http://doordash.com",
                "logoUrl": "https://bookface-images.s3.amazonaws.com/logos/doordash-logo.png",
                "industryTags": ["E-commerce", "Marketplace", "Logistics"],
                "status": "PUBLIC",
                "teamSize": "6000+",
                "location": "San Francisco",
                "founders": [
                    {
                        "name": "Tony Xu",
                        "title": "Co-founder, CEO",
                        "linkedinUrl": "https://www.linkedin.com/in/xutony/",
                        "twitterUrl": "https://twitter.com/t_xu",
                    },
                    {
                        "name": "Andy Fang",
                        "title": "Co-founder, CTO",
                        "linkedinUrl": "https://www.linkedin.com/in/andyfang1/",
                        "twitterUrl": "",
                    },
                    {
                        "name": "Stanley Tang",
                        "title": "Co-founder",
                        "linkedinUrl": "https://www.linkedin.com/in/stanleytang/",
                        "twitterUrl": "https://twitter.com/stanleytang",
                    },
                ],
            },
            # 2016 Cohort
            {
                "id": "12346",
                "name": "Instacart",
                "description": "Grocery delivery platform.",
                "batch": "S16",
                "url": "https://www.instacart.com",
                "logoUrl": "https://bookface-images.s3.amazonaws.com/logos/instacart-logo.png",
                "industryTags": ["E-commerce", "Logistics", "Marketplace"],
                "status": "PUBLIC",
                "teamSize": "3000+",
                "location": "San Francisco",
                "founders": [
                    {
                        "name": "Apoorva Mehta",
                        "title": "Founder, Executive Chairman",
                        "linkedinUrl": "https://www.linkedin.com/in/apoorvamehta/",
                        "twitterUrl": "https://twitter.com/apoorva_mehta",
                    },
                ],
            },
            # 2020 Cohort
            {
                "id": "12347",
                "name": "Virtually",
                "description": "Infrastructure for online schools.",
                "batch": "S20",
                "url": "https://tryvirtually.com",
                "logoUrl": "https://bookface-images.s3.amazonaws.com/logos/virtually-logo.png",
                "industryTags": ["Education", "SaaS", "EdTech"],
                "status": "ACTIVE",
                "teamSize": "10-50",
                "location": "San Francisco",
                "founders": [
                    {
                        "name": "Ish Baid",
                        "title": "Founder, CEO",
                        "linkedinUrl": "https://www.linkedin.com/in/ishbaid/",
                        "twitterUrl": "https://twitter.com/ishbaid",
                    },
                ],
            },
            # 2022 Cohort
            {
                "id": "12348",
                "name": "Peerlist",
                "description": "A professional network for the modern workforce.",
                "batch": "W22",
                "url": "https://peerlist.io",
                "logoUrl": "https://bookface-images.s3.amazonaws.com/logos/peerlist-logo.png",
                "industryTags": ["Professional Network", "Recruiting", "Social"],
                "status": "ACTIVE",
                "teamSize": "10-50",
                "location": "Remote",
                "founders": [
                    {
                        "name": "Akash Bhadange",
                        "title": "Co-founder, CEO",
                        "linkedinUrl": "https://www.linkedin.com/in/akashbhadange/",
                        "twitterUrl": "https://twitter.com/akashbhadange",
                    },
                    {
                        "name": "Yogini Bende",
                        "title": "Co-founder, COO",
                        "linkedinUrl": "https://www.linkedin.com/in/yoginibende/",
                        "twitterUrl": "https://twitter.com/yoginibende",
                    },
                ],
            },
            # 2023 Cohort - Modified to demonstrate updates
            {
                "id": "12345",
                "name": "TestAI",
                "description": "AI platform for testing and development - UPDATED DESCRIPTION.",
                "batch": "W23",
                "url": "http://testai.dev",
                "logoUrl": "https://example.com/newlogo.png",
                "industryTags": ["AI", "Developer Tools", "Machine Learning"],
                "status": "ACQUIRED",
                "teamSize": "50-100",
                "location": "New York",
                "founders": [
                    {
                        "name": "Test Founder",
                        "title": "CEO",
                        "linkedinUrl": "https://www.linkedin.com/in/testfounder/",
                        "twitterUrl": "https://twitter.com/testfounder",
                    },
                    {
                        "name": "New Founder",
                        "title": "CTO",
                        "linkedinUrl": "https://www.linkedin.com/in/newfounder/",
                        "twitterUrl": "https://twitter.com/newfounder",
                    },
                ],
            },
        ]

        # If year filter is applied, filter by year
        if year:
            filtered_startups = []
            for startup in sample_startups:
                batch = startup.get("batch", "")
                if batch:
                    match = re.search(r"([WS])(\d{2})", batch)
                    if match:
                        year_short = match.group(2)
                        startup_year = int("20" + year_short)
                        if startup_year == year:
                            filtered_startups.append(startup)
            sample_startups = filtered_startups
            logger.info(f"Filtered to {len(sample_startups)} startups from year {year}")

        # Process the raw data just like we would with real API data
        processed_startups = []
        logger.info(f"Processing {len(sample_startups)} sample startups...")

        for idx, startup in enumerate(sample_startups):
            try:
                self.processed_startups = idx + 1
                processed_data = self.process_startup_data(startup)

                # Save to database (this tracks changes)
                self._save_startup_to_db(processed_data)

                processed_startups.append(processed_data)
            except Exception as e:
                logger.error(
                    f"Error processing sample startup {startup.get('name', 'Unknown')}: {e}"
                )

        # Update total count in stats
        self.stats["total"] = len(processed_startups)
        logger.info(f"Successfully processed {len(processed_startups)} sample startups")
        logger.info(
            f"Stats: Added={self.stats['added']}, Updated={self.stats['updated']}, Unchanged={self.stats['unchanged']}"
        )

        return processed_startups
