#!/usr/bin/env python3
"""
- Simple script to check database contents, instead of having to run sqlite3 shell.
- good for dev, debugging, and small db.

1. Accesses your database using the same SQLAlchemy models your application uses
2. Formats the data in a readable way
3. Shows the relationships between startups and founders

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

from app import create_app
from app.models.startup import Startup, Founder

# Create and configure the Flask app
app = create_app()

# Use app context for database operations
with app.app_context():
    print("STARTUPS IN DATABASE:")
    print("=====================")
    startups = Startup.query.all()
    for s in startups:
        print(f"ID: {s.id}")
        print(f"Name: {s.name}")
        print(f"Description: {s.description}")
        print(f"Year: {s.year_founded}")
        print(f"Batch: {s.batch}")
        print(f"Status: {s.status}")
        print(f"Location: {s.location}")
        print(f"Tags: {s.tags}")
        print(f"Team Size: {s.team_size}")
        print(f"Founders: {len(s.founders)}")
        print("----------------------")
        for f in s.founders:
            print(f"  - {f.name} ({f.title})")
        print("\n")
