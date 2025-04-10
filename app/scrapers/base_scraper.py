from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """Abstract base class for all startup data scrapers"""

    def __init__(self):
        self.source_name = None

    @abstractmethod
    def fetch_startups(self, year=None):
        """
        Fetch startups from the source

        Args:
            year (int, optional): Filter startups by year

        Returns:
            list: List of startup dictionaries
        """
        pass

    @abstractmethod
    def process_startup_data(self, raw_data):
        """
        Process raw startup data into a standardized format

        Args:
            raw_data: Raw data from the source

        Returns:
            dict: Processed startup data in standardized format
        """
        pass

    def get_source_name(self):
        """Get the name of the data source"""
        return self.source_name
