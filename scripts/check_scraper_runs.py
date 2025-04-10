#!/usr/bin/env python3
"""
Script to check scraper run history
"""

import os
import sys
import time

# Add the parent directory to sys.path to allow imports from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models.scraper_run import ScraperRun
from tabulate import tabulate
from datetime import datetime

# Create and configure the Flask app
app = create_app()

# Use app context for database operations
with app.app_context():
    print("SCRAPER RUN HISTORY:")
    print("====================")

    # Get all runs sorted by start time (most recent first)
    runs = ScraperRun.query.order_by(ScraperRun.start_time.desc()).all()

    if not runs:
        print("No scraper runs recorded yet.")
    else:
        # Format data for tabulate
        data = []
        for run in runs:
            # Calculate duration if both start and end times exist
            duration = "N/A"
            if run.start_time and run.end_time:
                duration = str(run.end_time - run.start_time)

            # Format timestamps
            start_time = (
                run.start_time.strftime("%Y-%m-%d %H:%M:%S")
                if run.start_time
                else "N/A"
            )

            data.append(
                [
                    run.id,
                    run.source,
                    run.status,
                    start_time,
                    duration,
                    run.startups_added,
                    run.startups_updated,
                    run.startups_unchanged,
                    run.total_processed,
                ]
            )

        # Print table
        headers = [
            "ID",
            "Source",
            "Status",
            "Start Time",
            "Duration",
            "Added",
            "Updated",
            "Unchanged",
            "Total",
        ]
        print(tabulate(data, headers=headers, tablefmt="simple"))

        print(f"\nTotal runs: {len(runs)}")
