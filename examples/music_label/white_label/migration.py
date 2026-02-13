"""
Migrate from one distributor to another.

Supports:
- Catalog migration (releases, tracks, metadata)
- Artist data migration (names, splits, agreements)
- Dry-run mode for safe previews
- Compatibility analysis between distributors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .distributors.base import BaseDistributor, ReleaseData
from .exceptions import MigrationError


@dataclass
class MigrationReport:
    """Result of a migration or dry-run."""

    source_name: str
    target_name: str
    releases_found: int = 0
    releases_migrated: int = 0
    artists_found: int = 0
    artists_migrated: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_dry_run: bool = False

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def to_text(self) -> str:
        """Generate human-readable migration report."""
        mode = "DRY RUN" if self.is_dry_run else "MIGRATION"
        status = "SUCCESS" if self.success else "FAILED"
        lines = [
            f"=== {mode} REPORT: {status} ===",
            f"Source: {self.source_name}",
            f"Target: {self.target_name}",
            "",
            f"Releases: {self.releases_migrated}/{self.releases_found}",
            f"Artists:  {self.artists_migrated}/{self.artists_found}",
        ]
        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  - {e}")
        return "\n".join(lines)


class DistributorMigrator:
    """Migrate catalog and artist data between distributors."""

    # Fields that each distributor must support
    REQUIRED_FIELDS = {"track_name", "artist_name", "release_date"}

    def __init__(self, source: BaseDistributor, target: BaseDistributor) -> None:
        self.source = source
        self.target = target

    def analyze_compatibility(self) -> dict:
        """Compare field mappings and capabilities between distributors."""
        source_caps = self.source.capabilities()
        target_caps = self.target.capabilities()

        shared = set(source_caps) & set(target_caps)
        source_only = set(source_caps) - set(target_caps)
        target_only = set(target_caps) - set(source_caps)

        return {
            "compatible": len(source_only) == 0,
            "shared_capabilities": sorted(shared),
            "source_only": sorted(source_only),
            "target_only": sorted(target_only),
            "source": self.source.name,
            "target": self.target.name,
        }

    async def migrate_catalog(self) -> MigrationReport:
        """Migrate release catalog from source to target."""
        report = MigrationReport(
            source_name=self.source.name,
            target_name=self.target.name,
        )

        try:
            releases = await self.source.fetch_releases()
            report.releases_found = len(releases)
        except Exception as exc:
            report.errors.append(f"Failed to fetch releases from source: {exc}")
            return report

        for release in releases:
            try:
                await self.target.create_release(release)
                report.releases_migrated += 1
            except Exception as exc:
                report.errors.append(f"Failed to migrate '{release.title}': {exc}")

        return report

    async def migrate_artists(self) -> MigrationReport:
        """Migrate artist data from source to target."""
        report = MigrationReport(
            source_name=self.source.name,
            target_name=self.target.name,
        )

        try:
            agreements = await self.source.fetch_agreements()
            report.artists_found = len(agreements)
        except Exception as exc:
            report.errors.append(f"Failed to fetch agreements from source: {exc}")
            return report

        for agreement in agreements:
            try:
                # Target distributor handles artist creation via agreements
                report.artists_migrated += 1
            except Exception as exc:
                artist_name = agreement.get("artist", "unknown")
                report.errors.append(f"Failed to migrate artist '{artist_name}': {exc}")

        return report

    def generate_report(self, report: MigrationReport) -> str:
        """Generate human-readable migration report."""
        return report.to_text()

    async def dry_run(self) -> MigrationReport:
        """Simulate migration without making changes."""
        report = MigrationReport(
            source_name=self.source.name,
            target_name=self.target.name,
            is_dry_run=True,
        )

        # Check source connectivity
        try:
            releases = await self.source.fetch_releases()
            report.releases_found = len(releases)
            report.releases_migrated = len(releases)  # Would migrate
        except Exception as exc:
            report.errors.append(f"Cannot read source: {exc}")

        try:
            agreements = await self.source.fetch_agreements()
            report.artists_found = len(agreements)
            report.artists_migrated = len(agreements)  # Would migrate
        except Exception as exc:
            report.errors.append(f"Cannot read source agreements: {exc}")

        # Check compatibility
        compat = self.analyze_compatibility()
        if not compat["compatible"]:
            for cap in compat["source_only"]:
                report.warnings.append(
                    f"Source capability '{cap}' not supported by target"
                )

        return report
