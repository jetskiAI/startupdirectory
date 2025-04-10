from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import os
import logging
import threading
from datetime import datetime

from app.scrapers.yc_scraper import YCombinatorScraper
from app.models.startup import Startup, Founder
from app.models.db import db
from app.models.scraper_run import ScraperRun

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Blueprint
admin_bp = Blueprint("admin", __name__)


# API key authentication
def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        # Get the API key from environment
        api_key = os.getenv("API_KEY")

        # Get the authorization header
        auth_header = request.headers.get("Authorization")

        # Check if the header is present and in correct format
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {"error": "Unauthorized - Missing or invalid Authorization header"}
                ),
                401,
            )

        # Extract the token
        token = auth_header.split(" ")[1]

        # Check if the token matches
        if token != api_key:
            return jsonify({"error": "Unauthorized - Invalid API key"}), 401

        # If everything checks out, proceed to the route
        return view_function(*args, **kwargs)

    return decorated_function


# Scraper functions mapped to their names
scraper_map = {
    "yc": YCombinatorScraper,
    # Add other scrapers as they are implemented
    # 'neo': NeoScraper,
    # 'techstars': TechStarsScraper,
}


def run_scraper(scraper_name, year=None):
    """Run a specific scraper in a separate thread"""
    logger.info(
        f"Starting scraper: {scraper_name}" + (f" for year {year}" if year else "")
    )

    # Create Flask app context
    with current_app.app_context():
        try:
            # Get the correct scraper class
            if scraper_name not in scraper_map:
                logger.error(f"Unknown scraper: {scraper_name}")
                return

            # Initialize the scraper
            scraper_class = scraper_map[scraper_name]
            scraper = scraper_class()

            # Fetch startups
            startups = scraper.fetch_startups(year)

            # Process and save each startup
            for startup_data in startups:
                # Extract founders data
                founders_data = startup_data.pop("founders", [])

                # Check if startup exists
                existing_startup = Startup.query.filter_by(
                    name=startup_data["name"], year_founded=startup_data["year_founded"]
                ).first()

                if existing_startup:
                    # Update existing startup
                    for key, value in startup_data.items():
                        setattr(existing_startup, key, value)
                    startup = existing_startup
                else:
                    # Create new startup
                    startup = Startup(**startup_data)
                    db.session.add(startup)

                # Need to flush to get the startup ID
                db.session.flush()

                # Process founders
                for founder_data in founders_data:
                    # Check if founder exists
                    existing_founder = Founder.query.filter_by(
                        name=founder_data["name"], startup_id=startup.id
                    ).first()

                    if existing_founder:
                        # Update existing founder
                        for key, value in founder_data.items():
                            setattr(existing_founder, key, value)
                    else:
                        # Create new founder
                        founder = Founder(**founder_data)
                        founder.startup_id = startup.id
                        db.session.add(founder)

                db.session.commit()

            logger.info(
                f"Completed scraper: {scraper_name}. Processed {len(startups)} startups."
            )

        except Exception as e:
            logger.error(f"Error in scraper {scraper_name}: {str(e)}")
            db.session.rollback()


@admin_bp.route("/scrape", methods=["POST"])
@require_api_key
def trigger_scrape():
    """Trigger a data scraping operation"""
    data = request.json

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    source = data.get("source")
    year = data.get("year")

    if not source:
        return jsonify({"error": "Missing source parameter"}), 400

    # Validate source
    if source != "all" and source not in scraper_map:
        return (
            jsonify(
                {
                    "error": f'Invalid source: {source}. Available sources: {", ".join(list(scraper_map.keys()) + ["all"])}.'
                }
            ),
            400,
        )

    if source == "all":
        # Start all scrapers in separate threads
        for scraper_name in scraper_map.keys():
            thread = threading.Thread(target=run_scraper, args=(scraper_name, year))
            thread.daemon = True
            thread.start()

        return (
            jsonify(
                {
                    "message": f"All scrapers started. Results will be processed asynchronously.",
                    "sources": list(scraper_map.keys()),
                    "year": year,
                }
            ),
            202,
        )
    else:
        # Start specific scraper in a separate thread
        thread = threading.Thread(target=run_scraper, args=(source, year))
        thread.daemon = True
        thread.start()

        return (
            jsonify(
                {
                    "message": f"Scraper {source} started. Results will be processed asynchronously.",
                    "source": source,
                    "year": year,
                }
            ),
            202,
        )


@admin_bp.route("/scraper/status", methods=["GET"])
def get_scraper_status():
    """Get status of scraper runs"""
    scraper_runs = (
        ScraperRun.query.order_by(ScraperRun.start_time.desc()).limit(10).all()
    )

    # Format the response
    runs = []
    for run in scraper_runs:
        runs.append(
            {
                "id": run.id,
                "source": run.source,
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "status": run.status,
                "startups_added": run.startups_added,
                "startups_updated": run.startups_updated,
                "startups_unchanged": run.startups_unchanged,
                "total_processed": run.total_processed,
                "error_message": run.error_message,
            }
        )

    # Get counts per source
    source_counts = {}
    sources = ["YC", "Neo", "TechStars"]

    for source in sources:
        count = Startup.query.filter_by(source=source).count()
        source_counts[source] = count

        # Get last successful run
        last_run = (
            ScraperRun.query.filter_by(source=source, status="success")
            .order_by(ScraperRun.end_time.desc())
            .first()
        )

        if last_run and last_run.end_time:
            days_since = (datetime.utcnow() - last_run.end_time).days
            source_counts[f"{source}_last_update"] = days_since
        else:
            source_counts[f"{source}_last_update"] = None

    return (
        jsonify(
            {"status": "success", "recent_runs": runs, "source_counts": source_counts}
        ),
        200,
    )


@admin_bp.route("/scraper/run", methods=["POST"])
def trigger_scraper_run():
    """Trigger a scraper run manually"""
    data = request.json
    source = data.get("source", "YC")
    year = data.get("year")
    force = data.get("force", False)

    # Validate source
    valid_sources = ["YC", "Neo", "TechStars", "all"]
    if source not in valid_sources:
        return (
            jsonify({"error": f"Invalid source. Must be one of {valid_sources}"}),
            400,
        )

    # This would ideally be run in a background task, but for simplicity,
    # we'll run it directly here (this will block the API call until complete)
    try:
        # Import here to avoid circular imports
        from scripts.collect_data import (
            collect_yc_data,
            collect_neo_data,
            collect_techstars_data,
        )

        result = {"status": "success", "startups_processed": 0, "sources_processed": []}

        if source == "YC" or source == "all":
            count = collect_yc_data(year, force)
            result["startups_processed"] += count
            result["sources_processed"].append("YC")

        if source == "Neo" or source == "all":
            count = collect_neo_data(year, force)
            result["startups_processed"] += count
            result["sources_processed"].append("Neo")

        if source == "TechStars" or source == "all":
            count = collect_techstars_data(year, force)
            result["startups_processed"] += count
            result["sources_processed"].append("TechStars")

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
