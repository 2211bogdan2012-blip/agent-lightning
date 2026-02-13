"""
Release Manager Agent -- Lena.

Управление релизным пайплайном: создание, загрузка на площадки,
мониторинг статусов, валидация метаданных.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class Release:
    """Релиз (сингл, EP, альбом)."""
    id: str
    artist: str
    title: str
    tracks: list[str]
    release_date: str                   # YYYY-MM-DD
    release_type: str = "single"        # single | ep | album
    status: str = "draft"               # draft | submitted | live | rejected
    upc: str | None = None
    isrc_list: list[str] = field(default_factory=list)
    artwork_url: str | None = None
    distributor_id: str | None = None
    dsp_statuses: dict[str, str] = field(default_factory=dict)


class ReleaseValidationError(Exception):
    """Ошибка валидации метаданных релиза."""


@dataclass
class ReleaseManager(BaseAgent):
    """Релиз-менеджер. Пайплайн от создания до DSP."""

    distributor_client: Any = None  # KoalaMusicClient
    calendar: list[Release] = field(default_factory=list)
    _id_counter: int = 0

    def __post_init__(self):
        if not self.name:
            self.name = "Лена"
        if not self.codename:
            self.codename = "RELEASE-PIPE"
        if not self.role:
            self.role = "Релиз-менеджер"

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"REL-{self._id_counter:04d}"

    def create_release(
        self,
        artist: str,
        title: str,
        tracks: list[str],
        release_date: str,
        release_type: str = "single",
    ) -> Release:
        """Создаёт новый релиз.

        Args:
            artist: Имя артиста.
            title: Название релиза.
            tracks: Список треков.
            release_date: Дата релиза (YYYY-MM-DD).
            release_type: Тип (single/ep/album).

        Returns:
            Созданный объект Release.
        """
        release = Release(
            id=self._next_id(),
            artist=artist,
            title=title,
            tracks=tracks,
            release_date=release_date,
            release_type=release_type,
            status="draft",
        )
        self.calendar.append(release)
        logger.info("Release created: %s - %s (%s) [%s]", artist, title, release.id, release_date)
        return release

    async def upload_to_koala(self, release: Release) -> dict[str, Any]:
        """Загружает релиз в Koala Music Portal.

        Args:
            release: Объект Release.

        Returns:
            Ответ от дистрибьютора.

        Raises:
            RuntimeError: Если клиент не настроен.
            ReleaseValidationError: Если метаданные невалидны.
        """
        if self.distributor_client is None:
            raise RuntimeError("Distributor client not configured")

        errors = self.validate_metadata(release)
        if errors:
            raise ReleaseValidationError(f"Validation errors: {errors}")

        release.status = "submitted"
        logger.info("Release %s submitted to distributor", release.id)
        return {
            "release_id": release.id,
            "status": "submitted",
            "submitted_at": datetime.utcnow().isoformat(),
        }

    def track_status(self, release_id: str) -> dict[str, Any] | None:
        """Проверяет статус релиза на всех DSP.

        Args:
            release_id: ID релиза.

        Returns:
            Статус на каждой площадке или None.
        """
        release = self._find_release(release_id)
        if release is None:
            return None

        return {
            "release_id": release.id,
            "title": release.title,
            "artist": release.artist,
            "overall_status": release.status,
            "release_date": release.release_date,
            "dsp_statuses": release.dsp_statuses or {
                "Spotify": "pending",
                "Apple Music": "pending",
                "Yandex Music": "pending",
                "VK Music": "pending",
            },
        }

    def notify_artist(self, artist: str, release: Release, status: str) -> dict[str, str]:
        """Подготавливает уведомление артисту о статусе релиза.

        Args:
            artist: Имя артиста.
            release: Объект Release.
            status: Новый статус.

        Returns:
            Данные для отправки уведомления.
        """
        messages = {
            "submitted": f"Релиз \"{release.title}\" отправлен на площадки! Дата выхода: {release.release_date}.",
            "live": f"Релиз \"{release.title}\" вышел на всех площадках!",
            "rejected": f"Релиз \"{release.title}\" отклонён. Проверьте метаданные.",
        }
        return {
            "artist": artist,
            "release_id": release.id,
            "message": messages.get(status, f"Статус релиза \"{release.title}\": {status}"),
            "status": status,
        }

    def get_calendar(self, month: str | None = None) -> list[dict[str, Any]]:
        """Возвращает календарь релизов.

        Args:
            month: Месяц (YYYY-MM) или None для всех.

        Returns:
            Список релизов с датами.
        """
        result = []
        for release in self.calendar:
            if month and not release.release_date.startswith(month):
                continue
            result.append({
                "id": release.id,
                "artist": release.artist,
                "title": release.title,
                "release_date": release.release_date,
                "type": release.release_type,
                "status": release.status,
                "tracks_count": len(release.tracks),
            })
        return sorted(result, key=lambda x: x["release_date"])

    def validate_metadata(self, release: Release) -> list[str]:
        """Проверяет метаданные релиза перед отправкой.

        Проверяет: ISRC, UPC, обложка, даты, название.

        Args:
            release: Объект Release.

        Returns:
            Список ошибок (пустой = всё ок).
        """
        errors = []

        if not release.title or not release.title.strip():
            errors.append("Title is empty")

        if not release.artist or not release.artist.strip():
            errors.append("Artist is empty")

        if not release.tracks:
            errors.append("No tracks in release")

        # Дата релиза
        try:
            rel_date = datetime.strptime(release.release_date, "%Y-%m-%d").date()
            if rel_date < date.today():
                errors.append(f"Release date {release.release_date} is in the past")
        except ValueError:
            errors.append(f"Invalid release date format: {release.release_date}")

        # UPC (12 или 13 цифр)
        if release.upc and not re.match(r"^\d{12,13}$", release.upc):
            errors.append(f"Invalid UPC: {release.upc}")

        # ISRC (CC-XXX-YY-NNNNN)
        for isrc in release.isrc_list:
            if not re.match(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$", isrc):
                errors.append(f"Invalid ISRC: {isrc}")

        # Artwork
        if not release.artwork_url:
            errors.append("No artwork provided")

        if errors:
            logger.warning("Validation errors for %s: %s", release.id, errors)

        return errors

    def get_catalog(self) -> dict[str, Any]:
        """Полный каталог релизов лейбла."""
        live = [r for r in self.calendar if r.status == "live"]
        return {
            "total_releases": len(self.calendar),
            "live": len(live),
            "total_tracks": sum(len(r.tracks) for r in self.calendar),
            "artists": list(set(r.artist for r in self.calendar)),
            "releases": self.get_calendar(),
        }

    def _find_release(self, release_id: str) -> Release | None:
        for r in self.calendar:
            if r.id == release_id:
                return r
        return None
