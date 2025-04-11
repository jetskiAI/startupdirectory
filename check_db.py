#!/usr/bin/env python3
"""
- Simple script to check database contents, instead of having to run sqlite3 shell.
- Features:
  - Paginates results (40 at a time)
  - Filters by year, name, or batch
  - Uses colorized output for better readability
  - Accesses your database using the same SQLAlchemy models
  - Shows the relationships between startups and founders

Usage:
  python check_db.py                     # Shows all startups, 40 at a time
  python check_db.py --year=2022         # Only shows startups from 2022
  python check_db.py --page=2            # Shows the second page of results
  python check_db.py --name="AI"         # Search for startups with "AI" in the name
  python check_db.py --batch="W22"       # Search for startups from W22 batch
  python check_db.py --year=2022 --page=2  # Combines filters

TODO:
For a large dataset, you might want to:
- Modify it to take command line arguments to filter results
- Add pagination (e.g., only show 10 records at a time)
- Create more targeted scripts (e.g., to find startups by name or batch)

Ultimately, there are better options for working with lots of data:
- Use the Flask API you've built (via browser or tools like Postman)
- Use a database GUI like DB Browser for SQLite
- Create a simple admin web interface
"""

import argparse
import sys
from sqlalchemy import or_
from app import create_app
from app.models.startup import Startup, Founder


# ANSI color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check database contents with pagination and filtering"
    )
    parser.add_argument("--year", type=int, help="Filter startups by year")
    parser.add_argument(
        "--name", type=str, help="Search by startup name (case insensitive)"
    )
    parser.add_argument(
        "--batch", type=str, help='Filter by specific batch (e.g., "W22")'
    )
    parser.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument(
        "--per-page", type=int, default=40, help="Items per page (default: 40)"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    return parser.parse_args()


def format_text(text, color, args):
    """Apply color formatting if colors are enabled"""
    if args.no_color:
        return text
    return f"{color}{text}{Colors.ENDC}"


def main():
    args = parse_args()
    page = max(1, args.page)  # Ensure page is at least 1
    per_page = args.per_page
    year = args.year
    name_search = args.name
    batch = args.batch

    # Create and configure the Flask app
    app = create_app()

    # Use app context for database operations
    with app.app_context():
        # Build the query with optional filters
        query = Startup.query

        # Apply filters if provided
        filters_applied = []

        if year:
            # Get last two digits of year for batch filtering
            short_year = str(year)[-2:]

            # Filter by either year_founded or batch containing the year
            query = query.filter(
                or_(
                    Startup.year_founded == year,
                    Startup.batch.like(f"W{short_year}%"),
                    Startup.batch.like(f"S{short_year}%"),
                )
            )
            filters_applied.append(f"year: {year}")

        if name_search:
            query = query.filter(Startup.name.ilike(f"%{name_search}%"))
            filters_applied.append(f"name: '{name_search}'")

        if batch:
            query = query.filter(Startup.batch.ilike(f"{batch}%"))
            filters_applied.append(f"batch: '{batch}'")

        # Get total count for pagination info
        total_count = query.count()
        if total_count == 0:
            if filters_applied:
                print(f"No startups found with filters: {', '.join(filters_applied)}.")
            else:
                print("No startups found in the database.")
            return

        # Calculate pagination values
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page

        # Apply pagination
        startups = query.order_by(Startup.id).offset(offset).limit(per_page).all()

        # Display header with pagination info
        filters_info = (
            f" with filters: {', '.join(filters_applied)}" if filters_applied else ""
        )
        header = f"STARTUPS IN DATABASE{filters_info}"
        pagination = (
            f"(Page {page}/{total_pages}, showing {len(startups)} of {total_count})"
        )

        print(format_text(f"{header} {pagination}", Colors.BOLD + Colors.HEADER, args))
        print(format_text("=" * 60, Colors.BOLD, args))

        # Display startups
        for s in startups:
            print(format_text(f"ID: {s.id}", Colors.BOLD, args))
            print(format_text(f"Name: {s.name}", Colors.BOLD + Colors.GREEN, args))
            print(f"Description: {s.description}")
            print(format_text(f"Year: {s.year_founded}", Colors.YELLOW, args))
            print(format_text(f"Batch: {s.batch}", Colors.YELLOW, args))
            print(f"Status: {s.status}")

            # Highlight location field with cyan color
            location_text = s.location if s.location else "Not specified"
            print(format_text(f"Location: {location_text}", Colors.CYAN, args))

            print(f"Tags: {s.tags}")
            print(f"Team Size: {s.team_size}")

            # Show founders with different formatting
            founder_count = len(s.founders)
            founder_text = f"Founders: {founder_count}"
            print(format_text(founder_text, Colors.BOLD + Colors.BLUE, args))

            print(format_text("----------------------", Colors.BOLD, args))
            for f in s.founders:
                print(format_text(f"  - {f.name} ", Colors.CYAN, args) + f"({f.title})")
            print("\n")

        # Display pagination navigation help
        print(format_text("Navigation:", Colors.BOLD, args))

        # Build the base command with all filters
        base_cmd = "python check_db.py"
        if year:
            base_cmd += f" --year={year}"
        if name_search:
            base_cmd += f' --name="{name_search}"'
        if batch:
            base_cmd += f' --batch="{batch}"'
        if args.no_color:
            base_cmd += " --no-color"

        if page < total_pages:
            next_cmd = f"{base_cmd} --page={page + 1}"
            print(f"Next page: {next_cmd}")

        if page > 1:
            prev_cmd = f"{base_cmd} --page={page - 1}"
            print(f"Previous page: {prev_cmd}")

        # Display first/last page commands if not on those pages
        if total_pages > 2 and page != 1:
            first_cmd = f"{base_cmd} --page=1"
            print(f"First page: {first_cmd}")

        if total_pages > 2 and page != total_pages:
            last_cmd = f"{base_cmd} --page={total_pages}"
            print(f"Last page: {last_cmd}")


if __name__ == "__main__":
    main()
