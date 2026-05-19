"""Provider ABC and shared types for the portal scanner."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class JobListing:
    title: str
    url: str
    company: str
    location: str


@dataclass
class PortalEntry:
    """One company entry from portals.yml."""
    name: str
    careers_url: str = ""
    api: str = ""
    title_filter: dict = None
    location_filter: dict = None

    def __post_init__(self):
        if self.title_filter is None:
            self.title_filter = {}
        if self.location_filter is None:
            self.location_filter = {}


class Provider(ABC):
    """Abstract base class for all portal scanner providers."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique provider identifier (e.g. 'greenhouse')."""

    @abstractmethod
    def detect(self, entry: PortalEntry) -> Optional[dict]:
        """Return a detection context dict if this provider handles the entry, else None."""

    @abstractmethod
    async def fetch(self, entry: PortalEntry, client: Any) -> list[JobListing]:
        """Fetch job listings for the given portal entry using the provided httpx client."""
