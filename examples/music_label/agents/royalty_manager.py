"""
Royalty Manager Agent -- Rita.

Расчёт квартальных выплат, генерация PDF/XLSX отчётов,
учёт авансов и индивидуальных сплитов для каждого артиста.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class ArtistPayout:
    """Результат расчёта выплаты артисту за квартал."""
    artist: str
    quarter: str
    gross_revenue: Decimal
    split_pct: Decimal
    artist_share: Decimal
    advance_deducted: Decimal
    net_payout: Decimal
    tracks_count: int = 0
    streams_count: int = 0


class RoyaltyCalculationError(Exception):
    """Ошибка при расчёте роялти."""


@dataclass
class RoyaltyManager(BaseAgent):
    """Менеджер по роялти. Расчёты, отчёты, авансы."""

    distributor_client: Any = None  # KoalaMusicClient
    db_connection: Any = None       # asyncpg.Connection
    report_templates: dict[str, str] = field(default_factory=dict)

    # Внутренний кеш данных
    _splits_cache: dict[str, Decimal] = field(default_factory=dict)
    _advances_cache: dict[str, Decimal] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            self.name = "Рита"
        if not self.codename:
            self.codename = "ROYALTY-ENGINE"
        if not self.role:
            self.role = "Менеджер по роялти"

    def apply_split(self, revenue: Decimal, artist: str) -> Decimal:
        """Применяет индивидуальный процент сплита к доходу.

        Args:
            revenue: Общий доход от трека/каталога.
            artist: Имя артиста.

        Returns:
            Доля артиста (revenue * split_pct).

        Raises:
            RoyaltyCalculationError: Если сплит не найден.
        """
        split_pct = self._splits_cache.get(artist)
        if split_pct is None:
            raise RoyaltyCalculationError(
                f"Split not found for artist '{artist}'. "
                "Check contracts or set default."
            )
        return (revenue * split_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate(
        self,
        quarter: str,
        artist: str | None = None,
        revenue_data: list[dict[str, Any]] | None = None,
    ) -> list[ArtistPayout]:
        """Основной расчёт роялти за квартал.

        Цепочка: загрузить данные -> применить сплиты -> вычесть авансы -> результат.

        Args:
            quarter: Квартал (напр. "Q4 2025").
            artist: Конкретный артист или None для всех.
            revenue_data: Данные о доходах (если уже загружены).

        Returns:
            Список ArtistPayout для каждого артиста.
        """
        if revenue_data is None:
            revenue_data = []

        results: list[ArtistPayout] = []

        # Группируем данные по артистам
        by_artist: dict[str, list[dict[str, Any]]] = {}
        for row in revenue_data:
            a = row.get("artist", "Unknown")
            if artist and a != artist:
                continue
            by_artist.setdefault(a, []).append(row)

        for artist_name, rows in by_artist.items():
            gross = Decimal("0")
            streams = 0
            tracks = set()

            for row in rows:
                amount = Decimal(str(row.get("revenue", 0)))
                gross += amount
                streams += int(row.get("streams", 0))
                track = row.get("track")
                if track:
                    tracks.add(track)

            try:
                artist_share = self.apply_split(gross, artist_name)
            except RoyaltyCalculationError:
                logger.warning("No split for %s, skipping", artist_name)
                continue

            advance = self._advances_cache.get(artist_name, Decimal("0"))
            deducted = min(advance, artist_share)
            net = artist_share - deducted

            results.append(ArtistPayout(
                artist=artist_name,
                quarter=quarter,
                gross_revenue=gross,
                split_pct=self._splits_cache.get(artist_name, Decimal("0")),
                artist_share=artist_share,
                advance_deducted=deducted,
                net_payout=net,
                tracks_count=len(tracks),
                streams_count=streams,
            ))

        logger.info("Calculated royalties for Q=%s: %d artists", quarter, len(results))
        return results

    def generate_report(
        self,
        artist: str,
        quarter: str,
        fmt: str = "pdf",
        payouts: list[ArtistPayout] | None = None,
    ) -> dict[str, Any]:
        """Генерирует отчёт для артиста.

        Args:
            artist: Имя артиста.
            quarter: Квартал.
            fmt: Формат ("pdf" или "xlsx").
            payouts: Данные (если уже рассчитаны).

        Returns:
            Мета-информация об отчёте (путь, формат, размер).
        """
        payout = None
        if payouts:
            payout = next((p for p in payouts if p.artist == artist), None)

        report_data = {
            "artist": artist,
            "quarter": quarter,
            "format": fmt,
            "generated_at": datetime.utcnow().isoformat(),
            "payout": {
                "gross_revenue": str(payout.gross_revenue) if payout else "0",
                "split_pct": str(payout.split_pct) if payout else "0",
                "artist_share": str(payout.artist_share) if payout else "0",
                "advance_deducted": str(payout.advance_deducted) if payout else "0",
                "net_payout": str(payout.net_payout) if payout else "0",
            },
            "filename": f"royalty_{artist}_{quarter.replace(' ', '_')}.{fmt}",
        }
        logger.info("Report generated: %s", report_data["filename"])
        return report_data

    def check_advances(self, artist: str | None = None) -> list[dict[str, Any]]:
        """Возвращает список активных авансов.

        Args:
            artist: Конкретный артист или None для всех.

        Returns:
            Список авансов с остатками.
        """
        result = []
        for name, balance in self._advances_cache.items():
            if artist and name != artist:
                continue
            if balance > 0:
                result.append({
                    "artist": name,
                    "remaining_balance": str(balance),
                    "status": "active",
                })
        return result

    def reconcile(
        self,
        quarter: str,
        calculated: list[ArtistPayout] | None = None,
        actual_payouts: dict[str, Decimal] | None = None,
    ) -> list[dict[str, Any]]:
        """Сверяет рассчитанные выплаты с фактическими.

        Args:
            quarter: Квартал.
            calculated: Рассчитанные выплаты.
            actual_payouts: Фактические суммы по артистам.

        Returns:
            Список расхождений.
        """
        if not calculated or not actual_payouts:
            return []

        discrepancies = []
        for payout in calculated:
            actual = actual_payouts.get(payout.artist)
            if actual is None:
                discrepancies.append({
                    "artist": payout.artist,
                    "quarter": quarter,
                    "type": "missing_actual",
                    "calculated": str(payout.net_payout),
                })
            elif actual != payout.net_payout:
                diff = actual - payout.net_payout
                discrepancies.append({
                    "artist": payout.artist,
                    "quarter": quarter,
                    "type": "amount_mismatch",
                    "calculated": str(payout.net_payout),
                    "actual": str(actual),
                    "difference": str(diff),
                })

        if discrepancies:
            logger.warning("Reconciliation: %d discrepancies for %s", len(discrepancies), quarter)
        return discrepancies

    async def fetch_koala_data(self, quarter: str) -> list[dict[str, Any]]:
        """Загружает данные из Koala Music API.

        Args:
            quarter: Квартал для загрузки.

        Returns:
            Список записей с доходами.

        Raises:
            RuntimeError: Если клиент дистрибьютора не настроен.
        """
        if self.distributor_client is None:
            raise RuntimeError("Distributor client not configured")

        data = await self.distributor_client.fetch_ofa_data(
            sheet_id="royalty",
            quarter=quarter,
        )
        logger.info("Fetched %d records from Koala for %s", len(data), quarter)
        return data

    def get_artist_balance(self, artist: str) -> dict[str, str]:
        """Текущий неоплаченный баланс артиста."""
        advance = self._advances_cache.get(artist, Decimal("0"))
        return {
            "artist": artist,
            "advance_remaining": str(advance),
            "status": "has_advance" if advance > 0 else "clear",
        }

    def set_split(self, artist: str, split_pct: float) -> None:
        """Устанавливает сплит для артиста (для тестирования)."""
        self._splits_cache[artist] = Decimal(str(split_pct))

    def set_advance(self, artist: str, amount: float) -> None:
        """Устанавливает аванс для артиста (для тестирования)."""
        self._advances_cache[artist] = Decimal(str(amount))
