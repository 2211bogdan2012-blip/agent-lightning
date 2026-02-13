"""
Analytics Agent -- Denis.

Анализ стримов, доходов, трендов. QoQ сравнения,
прогнозирование, еженедельные и ежемесячные дайджесты.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class StreamData:
    """Данные о стримах за период."""
    artist: str
    quarter: str
    streams: int
    revenue: float
    platform: str = ""
    country: str = ""
    track: str = ""


@dataclass
class AnalyticsAgent(BaseAgent):
    """Аналитик. Стримы, тренды, прогнозы, дайджесты."""

    db_connection: Any = None
    olap_client: Any = None
    _data: list[StreamData] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            self.name = "Денис"
        if not self.codename:
            self.codename = "ANALYTICS-AI"
        if not self.role:
            self.role = "Аналитик"

    def load_data(self, data: list[StreamData]) -> None:
        """Загружает данные для анализа."""
        self._data.extend(data)

    def analyze_streams(
        self,
        artist: str | None = None,
        quarter: str | None = None,
    ) -> dict[str, Any]:
        """Анализ стримов с группировкой по артисту и кварталу.

        Args:
            artist: Фильтр по артисту.
            quarter: Фильтр по кварталу.

        Returns:
            Сводка: total_streams, total_revenue, by_artist, by_quarter.
        """
        filtered = self._filter(artist, quarter)

        by_artist: dict[str, dict[str, Any]] = {}
        by_quarter: dict[str, dict[str, Any]] = {}

        for d in filtered:
            # По артистам
            if d.artist not in by_artist:
                by_artist[d.artist] = {"streams": 0, "revenue": 0.0}
            by_artist[d.artist]["streams"] += d.streams
            by_artist[d.artist]["revenue"] += d.revenue

            # По кварталам
            if d.quarter not in by_quarter:
                by_quarter[d.quarter] = {"streams": 0, "revenue": 0.0}
            by_quarter[d.quarter]["streams"] += d.streams
            by_quarter[d.quarter]["revenue"] += d.revenue

        total_streams = sum(d.streams for d in filtered)
        total_revenue = sum(d.revenue for d in filtered)

        return {
            "total_streams": total_streams,
            "total_revenue": round(total_revenue, 2),
            "artists_count": len(by_artist),
            "quarters_count": len(by_quarter),
            "by_artist": by_artist,
            "by_quarter": by_quarter,
        }

    def detect_trends(self, artist: str, periods: int = 4) -> dict[str, Any]:
        """Определяет тренды QoQ для артиста.

        Сравнивает последовательные кварталы и рассчитывает
        процент роста/падения.

        Args:
            artist: Имя артиста.
            periods: Количество кварталов для анализа.

        Returns:
            Тренд: direction, changes, average_growth.
        """
        data = [d for d in self._data if d.artist == artist]
        if not data:
            return {"artist": artist, "trend": "no_data", "periods": 0}

        # Группируем по кварталам
        quarterly: dict[str, int] = {}
        for d in data:
            quarterly.setdefault(d.quarter, 0)
            quarterly[d.quarter] += d.streams

        # Сортируем кварталы
        sorted_quarters = sorted(quarterly.keys())[-periods:]
        if len(sorted_quarters) < 2:
            return {"artist": artist, "trend": "insufficient_data", "periods": len(sorted_quarters)}

        changes = []
        for i in range(1, len(sorted_quarters)):
            prev_q = sorted_quarters[i - 1]
            curr_q = sorted_quarters[i]
            prev_val = quarterly[prev_q]
            curr_val = quarterly[curr_q]
            if prev_val > 0:
                pct_change = round((curr_val - prev_val) / prev_val * 100, 1)
            else:
                pct_change = 100.0 if curr_val > 0 else 0.0
            changes.append({
                "from": prev_q,
                "to": curr_q,
                "change_pct": pct_change,
            })

        avg_growth = sum(c["change_pct"] for c in changes) / len(changes)
        if avg_growth > 5:
            direction = "growing"
        elif avg_growth < -5:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "artist": artist,
            "trend": direction,
            "average_growth_pct": round(avg_growth, 1),
            "periods": len(sorted_quarters),
            "changes": changes,
        }

    def forecast(self, artist: str, quarters_ahead: int = 2) -> dict[str, Any]:
        """Простой линейный прогноз стримов.

        Использует среднее изменение за последние кварталы
        для экстраполяции на будущее.

        Args:
            artist: Имя артиста.
            quarters_ahead: Сколько кварталов прогнозировать.

        Returns:
            Прогноз по кварталам.
        """
        data = [d for d in self._data if d.artist == artist]
        if not data:
            return {"artist": artist, "forecast": [], "method": "linear"}

        quarterly: dict[str, int] = {}
        for d in data:
            quarterly.setdefault(d.quarter, 0)
            quarterly[d.quarter] += d.streams

        sorted_q = sorted(quarterly.keys())
        if len(sorted_q) < 2:
            return {"artist": artist, "forecast": [], "method": "linear", "reason": "need 2+ quarters"}

        # Среднее абсолютное изменение
        deltas = []
        for i in range(1, len(sorted_q)):
            deltas.append(quarterly[sorted_q[i]] - quarterly[sorted_q[i - 1]])
        avg_delta = sum(deltas) / len(deltas)

        last_value = quarterly[sorted_q[-1]]
        forecasts = []
        for i in range(1, quarters_ahead + 1):
            predicted = max(0, int(last_value + avg_delta * i))
            forecasts.append({
                "quarter_offset": f"+{i}",
                "predicted_streams": predicted,
            })

        return {
            "artist": artist,
            "method": "linear",
            "base_quarter": sorted_q[-1],
            "base_streams": last_value,
            "avg_delta": int(avg_delta),
            "forecast": forecasts,
        }

    def generate_digest(self, period: str = "weekly") -> dict[str, Any]:
        """Еженедельный или ежемесячный дайджест.

        Args:
            period: "weekly" или "monthly".

        Returns:
            Дайджест с основными метриками.
        """
        analysis = self.analyze_streams()
        top = self.top_tracks(n=5)

        return {
            "period": period,
            "generated_at": datetime.utcnow().isoformat(),
            "total_streams": analysis["total_streams"],
            "total_revenue": analysis["total_revenue"],
            "artists_active": analysis["artists_count"],
            "top_tracks": top,
            "highlights": self._generate_highlights(analysis),
        }

    def top_tracks(self, n: int = 10, quarter: str | None = None) -> list[dict[str, Any]]:
        """Топ N треков по стримам.

        Args:
            n: Количество треков.
            quarter: Фильтр по кварталу.

        Returns:
            Список треков с количеством стримов.
        """
        filtered = self._filter(quarter=quarter)
        track_streams: dict[str, dict[str, Any]] = {}

        for d in filtered:
            key = d.track or f"{d.artist} - unknown"
            if key not in track_streams:
                track_streams[key] = {"track": key, "artist": d.artist, "streams": 0, "revenue": 0.0}
            track_streams[key]["streams"] += d.streams
            track_streams[key]["revenue"] += d.revenue

        sorted_tracks = sorted(track_streams.values(), key=lambda x: x["streams"], reverse=True)
        return sorted_tracks[:n]

    def platform_breakdown(self, artist: str | None = None) -> dict[str, dict[str, Any]]:
        """Разбивка доходов по платформам.

        Args:
            artist: Фильтр по артисту.

        Returns:
            {platform: {streams, revenue, share_pct}}.
        """
        filtered = self._filter(artist=artist)
        platforms: dict[str, dict[str, Any]] = {}

        total_revenue = 0.0
        for d in filtered:
            plat = d.platform or "unknown"
            if plat not in platforms:
                platforms[plat] = {"streams": 0, "revenue": 0.0}
            platforms[plat]["streams"] += d.streams
            platforms[plat]["revenue"] += d.revenue
            total_revenue += d.revenue

        # Добавляем долю в процентах
        for plat_data in platforms.values():
            plat_data["revenue"] = round(plat_data["revenue"], 2)
            plat_data["share_pct"] = (
                round(plat_data["revenue"] / total_revenue * 100, 1)
                if total_revenue > 0 else 0.0
            )

        return platforms

    def geography_report(self, artist: str | None = None) -> dict[str, dict[str, Any]]:
        """Топ стран по стримам.

        Args:
            artist: Фильтр по артисту.

        Returns:
            {country: {streams, revenue}}.
        """
        filtered = self._filter(artist=artist)
        countries: dict[str, dict[str, Any]] = {}

        for d in filtered:
            country = d.country or "unknown"
            if country not in countries:
                countries[country] = {"streams": 0, "revenue": 0.0}
            countries[country]["streams"] += d.streams
            countries[country]["revenue"] += d.revenue

        # Округляем
        for c_data in countries.values():
            c_data["revenue"] = round(c_data["revenue"], 2)

        return countries

    def calculate_rps(self, artist: str | None = None) -> dict[str, Any]:
        """Revenue Per Stream (доход на стрим).

        Args:
            artist: Фильтр по артисту.

        Returns:
            RPS общий и по артистам.
        """
        analysis = self.analyze_streams(artist=artist)
        total_streams = analysis["total_streams"]
        total_revenue = analysis["total_revenue"]

        overall_rps = round(total_revenue / total_streams, 6) if total_streams > 0 else 0

        by_artist_rps = {}
        for name, data in analysis["by_artist"].items():
            streams = data["streams"]
            revenue = data["revenue"]
            by_artist_rps[name] = round(revenue / streams, 6) if streams > 0 else 0

        return {
            "overall_rps": overall_rps,
            "total_streams": total_streams,
            "total_revenue": total_revenue,
            "by_artist": by_artist_rps,
        }

    def _filter(
        self,
        artist: str | None = None,
        quarter: str | None = None,
    ) -> list[StreamData]:
        """Внутренний фильтр данных."""
        result = self._data
        if artist:
            result = [d for d in result if d.artist == artist]
        if quarter:
            result = [d for d in result if d.quarter == quarter]
        return result

    def _generate_highlights(self, analysis: dict[str, Any]) -> list[str]:
        """Генерирует текстовые хайлайты для дайджеста."""
        highlights = []
        if analysis["total_streams"] > 0:
            highlights.append(f"Total streams: {analysis['total_streams']:,}")
        if analysis["total_revenue"] > 0:
            highlights.append(f"Total revenue: {analysis['total_revenue']:,.2f} RUB")
        if analysis["artists_count"] > 0:
            highlights.append(f"Active artists: {analysis['artists_count']}")
        return highlights
