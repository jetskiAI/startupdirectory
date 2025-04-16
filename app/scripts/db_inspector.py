import sys
import os
from datetime import datetime
from sqlalchemy import inspect
from sqlalchemy.sql import func
import re

"""
Purpose: Debugging and data validation tool
Features:
- Detailed database statistics
- Raw data inspection
- Company name cleaning functionality
- Debugging helpers
- Comprehensive data validation
Design: Optimized for developers and debugging
"""
# Add the parent directory to the Python path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app import create_app
from app.models.db import db
from app.models.startup import Startup, Founder
from app.models.scraper_run import ScraperRun


def debug_value(value, field_name):
    """Debug helper to show raw values"""
    if value is None:
        return f"None ({field_name})"
    if isinstance(value, str):
        return f"'{value}' ({field_name})"
    if isinstance(value, (int, float)):
        return f"{value} ({field_name})"
    if isinstance(value, list):
        return f"{value} ({field_name})"
    return f"{value} ({field_name})"


def clean_company_name(name, location):
    """Remove location from company name if it exists at the end"""
    if not name or not location:
        return name

    # Debug print
    print(f"\nDebug - Name before cleaning: '{name}'")
    print(f"Debug - Location: '{location}'")

    # First try to handle cases where location is directly appended to name
    # e.g., "WhatnotLos Angeles, CA, USA"
    if location and location in name:
        # Try to find where the company name ends and location begins
        location_parts = location.split(",")
        if len(location_parts) > 0:
            first_part = location_parts[0].strip()  # e.g., "Los Angeles"
            if first_part in name:
                # Find the index where the location starts
                loc_index = name.find(first_part)
                if loc_index > 0:  # Make sure we're not at the start of the string
                    cleaned = name[:loc_index].strip()
                    print(f"Debug - Cleaned name (direct append): '{cleaned}'")
                    return cleaned

    # Handle cases where location might be in different formats
    location_variants = [
        location,
        location.replace(",", ""),
        location.split(",")[0],  # Just the city
        location.split(",")[0].strip() + ",",  # City with comma
        location.split(",")[0].strip() + " ",  # City with space
    ]

    for loc in location_variants:
        if loc and loc.strip() in name:
            cleaned = name.replace(loc.strip(), "").strip().rstrip(",")
            print(f"Debug - Cleaned name (variant match): '{cleaned}'")
            return cleaned

    # Common location patterns
    location_patterns = [
        # US States with optional city
        r",?\s*(?:Los\sAngeles|San\sFrancisco|New\sYork|Chicago|Boston|Seattle|Austin|Miami|Toronto|Vancouver|London|Berlin|Paris|Amsterdam|Stockholm|Copenhagen|Zurich|Tel\sAviv|Bangalore|Singapore|Tokyo|Sydney)?,?\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b",
        # US State Names with optional city
        r",?\s*(?:Los\sAngeles|San\sFrancisco|New\sYork|Chicago|Boston|Seattle|Austin|Miami|Toronto|Vancouver|London|Berlin|Paris|Amsterdam|Stockholm|Copenhagen|Zurich|Tel\sAviv|Bangalore|Singapore|Tokyo|Sydney)?,?\s*(?:Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New\sHampshire|New\sJersey|New\sMexico|New\sYork|North\sCarolina|North\sDakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode\sIsland|South\sCarolina|South\sDakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West\sVirginia|Wisconsin|Wyoming)\b",
        # Major Cities with optional country
        r",?\s*(?:Los\sAngeles|San\sFrancisco|New\sYork|Chicago|Boston|Seattle|Austin|Miami|Toronto|Vancouver|London|Berlin|Paris|Amsterdam|Stockholm|Copenhagen|Zurich|Tel\sAviv|Bangalore|Singapore|Tokyo|Sydney),?\s*(?:USA|US|UK|CA|DE|FR|NL|SE|DK|CH|IL|IN|SG|JP|AU)?\b",
        # Country Codes
        r",?\s*(?:USA|US|UK|CA|DE|FR|NL|SE|DK|CH|IL|IN|SG|JP|AU)\b",
        # Country Names
        r",?\s*(?:United\sStates|United\sKingdom|Canada|Germany|France|Netherlands|Sweden|Denmark|Switzerland|Israel|India|Singapore|Japan|Australia)\b",
        # Remote/Online
        r",?\s*(?:Remote|Online|Virtual|Digital)\b",
    ]

    # Try regex patterns
    for pattern in location_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            cleaned = re.sub(pattern, "", name, flags=re.IGNORECASE).strip().rstrip(",")
            print(f"Debug - Cleaned name (regex match): '{cleaned}'")
            return cleaned

    print(f"Debug - No cleaning applied")
    return name


def format_value(value, field_name=None):
    """Format value for display, handling None and empty values"""
    if value is None:
        return "Not available"
    if isinstance(value, str) and not value.strip():
        return "Not available"
    if isinstance(value, (int, float)) and value == 0:
        return "Not available"
    if isinstance(value, list) and not value:
        return "Not available"
    return value


def display_startup_info(startup):
    """Display detailed information about a startup"""
    # Clean the company name
    clean_name = clean_company_name(startup.name, startup.location)

    print("\n" + "=" * 80)
    print(f"STARTUP: {clean_name}")
    print("=" * 80)

    # Basic Information
    print("\nBASIC INFORMATION:")
    print(f"ID: {startup.id}")
    print(f"Description: {startup.description}")
    print(f"Batch: {startup.batch}")
    print(f"Year Founded: {startup.year_founded}")
    print(f"Status: {startup.status}")
    print(f"Location: {startup.location}")
    print(f"URL: {startup.url}")
    print(f"Logo URL: {startup.logo_url}")

    # Company Details
    print("\nCOMPANY DETAILS:")
    print(f"Team Size: {startup.team_size if startup.team_size else 'Not specified'}")
    if startup.tags and isinstance(startup.tags, str):
        tag_list = startup.tags.split(",")
        print(f"Tags: {', '.join(tag_list)}")
    else:
        print(f"Tags: None")

    # Founders Information
    if startup.founders:
        print("\nFOUNDERS:")
        for founder in startup.founders:
            print(f"\n- {founder.name}")
            print(f"  Title: {founder.title if founder.title else 'Not specified'}")
            print(
                f"  Role Type: {founder.role_type if founder.role_type else 'Not specified'}"
            )

            # Social Links
            if any([founder.linkedin_url, founder.twitter_url, founder.github_url]):
                print("  Social Links:")
                if founder.linkedin_url:
                    print(f"    LinkedIn: {founder.linkedin_url}")
                if founder.twitter_url:
                    print(f"    Twitter: {founder.twitter_url}")
                if founder.github_url:
                    print(f"    GitHub: {founder.github_url}")

            if founder.bio:
                print(f"  Bio: {founder.bio}")
            if founder.background:
                print(f"  Background: {founder.background}")
    else:
        print("\nFOUNDERS: None")

    # Timestamps
    print("\nTIMESTAMPS:")
    print(f"Created: {startup.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Updated: {startup.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n" + "-" * 80)


def display_database_stats():
    """Display database statistics"""
    total_startups = Startup.query.count()
    total_founders = Founder.query.count()

    print("\n=== DATABASE STATISTICS ===")
    print(f"Total Startups: {total_startups}")
    print(f"Total Founders: {total_founders}")

    # Count startups by batch
    print("\nSTARTUPS BY BATCH:")
    batches = (
        db.session.query(Startup.batch, func.count(Startup.id))
        .group_by(Startup.batch)
        .all()
    )
    for batch, count in batches:
        print(f"{batch}: {count}")

    # Count startups by status
    print("\nSTARTUPS BY STATUS:")
    statuses = (
        db.session.query(Startup.status, func.count(Startup.id))
        .group_by(Startup.status)
        .all()
    )
    for status, count in statuses:
        print(f"{status}: {count}")

    # Count startups with team size
    print("\nSTARTUPS BY TEAM SIZE:")
    team_sizes = (
        db.session.query(Startup.team_size, func.count(Startup.id))
        .group_by(Startup.team_size)
        .all()
    )
    for size, count in team_sizes:
        if size is not None:
            # Handle both string and integer values
            try:
                # Try to convert to int and compare
                if int(size) > 0:
                    print(f"Team Size {size}: {count}")
            except (ValueError, TypeError):
                # If conversion fails, just display the value as is
                print(f"Team Size {size}: {count}")

    print("\n" + "=" * 80)


def main():
    """Main function to check database contents"""
    try:
        # Create Flask app context
        app = create_app()
        with app.app_context():
            # Display database statistics
            display_database_stats()

            # Display detailed information for all startups
            startups = Startup.query.all()
            print(f"\nDisplaying detailed information for {len(startups)} startups:")

            for startup in startups:
                display_startup_info(startup)

    except Exception as e:
        print(f"Error checking database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
