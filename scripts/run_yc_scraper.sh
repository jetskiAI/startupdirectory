#!/bin/bash
# Script to manually run YC data collection

# Go to project root
cd "$(dirname "$0")/.."

# Set default values
FORCE=0
YEAR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --force)
            FORCE=1
            shift
            ;;
        --year=*)
            YEAR="${key#*=}"
            shift
            ;;
        --year)
            YEAR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--year=YYYY]"
            exit 1
            ;;
    esac
done

# Build command based on arguments
CMD="python scripts/collect_data.py --source=yc"

if [ -n "$YEAR" ]; then
    CMD="$CMD --year $YEAR"
fi

if [ "$FORCE" -eq 1 ]; then
    CMD="$CMD --force"
fi

# Run the command
echo "Running: $CMD"
$CMD

# Check and print stats
echo "-------------------------"
echo "YC SCRAPER STATS"
echo "-------------------------"
python -c "
from app import create_app
from app.models.db import db
from app.models.startup import Startup
from app.models.scraper_run import ScraperRun
app = create_app()
with app.app_context():
    # Count startups
    total = Startup.query.filter_by(source='YC').count()
    print(f'Total YC startups in database: {total}')
    
    # Last run info
    last_run = ScraperRun.query.filter_by(source='YC').order_by(ScraperRun.end_time.desc()).first()
    if last_run:
        print(f'Last run: {last_run.start_time}')
        print(f'Status: {last_run.status}')
        print(f'Added: {last_run.startups_added}')
        print(f'Updated: {last_run.startups_updated}')
        print(f'Unchanged: {last_run.startups_unchanged}')
    else:
        print('No scraper runs recorded yet')
" 