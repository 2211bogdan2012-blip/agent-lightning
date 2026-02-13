"""Base distributor interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class StreamData:
    """A single stream/revenue data point."""

    track_name: str
    artist_name: str
    streams: int
    revenue: float
    platform: str
    country: str
    date: date


@dataclass
class ReleaseData:
    """A music release (single, EP, album)."""

    title: str
    artist: str
    tracks: list[str]
    release_date: date
    upc: Optional[str] = None
    status: str = "draft"
    metadata: dict = field(default_factory=dict)


class BaseDistributor(ABC):
    """Abstract base for music distribution platform adapters."""

    name: str = "base"

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the distributor API. Returns True on success."""
        ...

    @abstractmethod
    async def fetch_streams(
        self, quarter: str, artist: Optional[str] = None
    ) -> list[StreamData]:
        """Fetch streaming data for a quarter (e.g. 'Q4 2025')."""
        ...

    @abstractmethod
    async def fetch_releases(
        self, artist: Optional[str] = None
    ) -> list[ReleaseData]:
        """Fetch all releases, optionally filtered by artist."""
        ...

    @abstractmethod
    async def create_release(self, release: ReleaseData) -> str:
        """Create a new release. Returns release ID."""
        ...

    @abstractmethod
    async def get_release_status(self, release_id: str) -> dict:
        """Get status of a release across platforms."""
        ...

    @abstractmethod
    async def fetch_agreements(self) -> list[dict]:
        """Fetch artist agreements/contracts from the distributor."""
        ...

    def capabilities(self) -> list[str]:
        """Return list of supported capabilities for compatibility checks."""
        return [
            "fetch_streams",
            "fetch_releases",
            "create_release",
            "get_release_status",
            "fetch_agreements",
        ]
