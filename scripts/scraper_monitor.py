#!/usr/bin/env python3
"""
Startup Directory - Scraper Monitoring Tool

This script provides a simple visualization of scraping progress and statistics.
Run this in a separate terminal while scraping to monitor progress.
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime
from tabulate import tabulate
import argparse

# Add the parent directory to sys.path to allow imports from the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import app and models after setting up path
from app import create_app
from app.models.db import db
from app.models.startup import Startup, Founder


def get_stats_from_db():
    """Get statistics from the database"""
    stats = {}

    # Create app context
    app = create_app()
    with app.app_context():
        # Get startup counts
        stats["total_startups"] = Startup.query.count()
        stats["total_founders"] = Founder.query.count()

        # Get source breakdown
        sources = (
            db.session.query(Startup.source, db.func.count(Startup.id))
            .group_by(Startup.source)
            .all()
        )
        stats["sources"] = {source: count for source, count in sources}

        # Get year breakdown
        years = (
            db.session.query(Startup.year_founded, db.func.count(Startup.id))
            .group_by(Startup.year_founded)
            .order_by(Startup.year_founded.desc())
            .all()
        )
        stats["years"] = {year: count for year, count in years}

        # Get batch breakdown
        batches = (
            db.session.query(Startup.batch, db.func.count(Startup.id))
            .group_by(Startup.batch)
            .all()
        )
        stats["batches"] = {batch: count for batch, count in batches}

        # Get status breakdown
        statuses = (
            db.session.query(Startup.status, db.func.count(Startup.id))
            .group_by(Startup.status)
            .all()
        )
        stats["statuses"] = {status: count for status, count in statuses}

        # Get most recent updates
        recent = Startup.query.order_by(Startup.updated_at.desc()).limit(5).all()
        stats["recent"] = [
            {
                "name": s.name,
                "updated_at": (
                    s.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    if s.updated_at
                    else "N/A"
                ),
                "founders": len(s.founders),
            }
            for s in recent
        ]

    return stats


def display_stats(stats, clear_screen=True):
    """Display statistics in a nice format"""
    if clear_screen:
        os.system("cls" if os.name == "nt" else "clear")

    print("\n" + "=" * 80)
    print(
        f"🚀 STARTUP DIRECTORY - SCRAPER STATISTICS  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 80)

    print("\n📊 OVERALL STATS:")
    print(f"  Startups: {stats['total_startups']}")
    print(f"  Founders: {stats['total_founders']}")
    print(
        f"  Founder/Startup Ratio: {stats['total_founders']/stats['total_startups'] if stats['total_startups'] else 0:.2f}"
    )

    print("\n🏢 SOURCES:")
    source_data = [
        [source, count] for source, count in stats.get("sources", {}).items()
    ]
    print(tabulate(source_data, headers=["Source", "Count"], tablefmt="simple"))

    print("\n📅 YEARS:")
    year_data = [
        [year, count]
        for year, count in sorted(stats.get("years", {}).items(), reverse=True)
    ]
    print(tabulate(year_data[:10], headers=["Year", "Count"], tablefmt="simple"))
    if len(year_data) > 10:
        print(f"...and {len(year_data)-10} more years")

    print("\n📋 BATCHES:")
    batch_data = [
        [batch, count] for batch, count in sorted(stats.get("batches", {}).items())
    ]
    print(tabulate(batch_data[:10], headers=["Batch", "Count"], tablefmt="simple"))
    if len(batch_data) > 10:
        print(f"...and {len(batch_data)-10} more batches")

    print("\n🔄 RECENT UPDATES:")
    if stats.get("recent"):
        recent_data = [
            [s["name"], s["updated_at"], s["founders"]] for s in stats["recent"]
        ]
        print(
            tabulate(
                recent_data,
                headers=["Startup", "Updated At", "Founders"],
                tablefmt="simple",
            )
        )
    else:
        print("  No recent updates found")


def main():
    """Main entry point for the monitoring script"""
    parser = argparse.ArgumentParser(description="Monitor scraper progress")
    parser.add_argument(
        "--interval", type=int, default=5, help="Refresh interval in seconds"
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    try:
        if args.once:
            stats = get_stats_from_db()
            display_stats(stats)
        else:
            print(
                f"Monitoring database every {args.interval} seconds. Press Ctrl+C to stop."
            )
            while True:
                stats = get_stats_from_db()
                display_stats(stats)
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
