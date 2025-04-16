"""
- Used Flask-SQLAlchemy: This extension helps Flask talk to databases
- We defined models (Startup and Founder) that map to database tables
These models tell Flask how to store and retrieve data
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.db import db


class Startup(db.Model):
    """It defines the structure of the startup data in the database"""

    __tablename__ = "startups"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    year_founded = Column(Integer, nullable=False)
    url = Column(String(255), nullable=True)
    logo_url = Column(String(255), nullable=True)
    source = Column(String(50), nullable=True)  # YC, Neo, TechStars, TechCrunch
    industry = Column(String(100), nullable=True)

    # Additional fields
    batch = Column(String(10), nullable=True)  # e.g., "W23", "S22"
    status = Column(String(20), nullable=True)  # active, acquired, closed
    location = Column(String(100), nullable=True)  # HQ city/country
    tags = Column(String(255), nullable=True)  # Comma-separated tags/keywords
    team_size = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    founders = relationship("Founder", back_populates="startup")

    def __init__(self, **kwargs):
        """Custom initialization to ensure year_founded is never NULL"""
        # Set defaults for required fields before calling parent initializer
        if "year_founded" not in kwargs or kwargs["year_founded"] is None:
            # Try to extract year from batch
            batch = kwargs.get("batch", "")
            if (
                batch
                and len(batch) >= 3
                and batch[0]
                in [
                    "W",
                    "S",
                    "F",
                    "X",
                ]  # Include new batch prefixes F (Fall) and X (Summer)
                and batch[1:].isdigit()
            ):
                # Convert batch like 'S20' to year 2020
                kwargs["year_founded"] = 2000 + int(batch[1:])
            else:
                # Default to current year if no batch or invalid format
                kwargs["year_founded"] = datetime.utcnow().year

        # Call parent initializer with updated kwargs
        super(Startup, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Startup {self.name}>"


class Founder(db.Model):
    __tablename__ = "founders"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    title = Column(String(100), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    twitter_url = Column(String(255), nullable=True)

    # Additional fields
    github_url = Column(String(255), nullable=True)
    email = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    role_type = Column(String(50), nullable=True)  # technical/non-technical
    background = Column(Text, nullable=True)  # Previous companies/education

    startup_id = Column(Integer, ForeignKey("startups.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    startup = relationship("Startup", back_populates="founders")

    def __repr__(self):
        return f"<Founder {self.name}>"
