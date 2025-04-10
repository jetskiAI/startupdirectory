from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.models.db import db


class ScraperRun(db.Model):
    """Model for tracking scraper execution details and statistics"""

    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False)  # "YC", "Neo", "TechStars", etc.
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(
        String(20), default="in_progress"
    )  # "success", "failed", "in_progress"

    # Statistics
    startups_added = Column(Integer, default=0)
    startups_updated = Column(Integer, default=0)
    startups_unchanged = Column(Integer, default=0)
    total_processed = Column(Integer, default=0)

    # Error details
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ScraperRun {self.id} - {self.source} - {self.status}>"
