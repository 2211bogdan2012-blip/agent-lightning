"""
Contract Manager Agent -- Max.

CRUD контрактов, контроль сплитов, мониторинг сроков,
привязка файлов договоров из облачного хранилища.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class ContractRecord:
    """Запись о контракте артиста."""
    artist: str
    split_pct: float
    signed_date: str | None = None
    expiry_date: str | None = None
    file_path: str | None = None
    file_type: str = "pdf"       # pdf | docx | scan
    status: str = "active"       # active | expired | placeholder
    notes: str = ""


class ContractError(Exception):
    """Ошибка при работе с контрактами."""


@dataclass
class ContractManager(BaseAgent):
    """Менеджер контрактов. Хранение, парсинг, контроль сплитов."""

    storage_client: Any = None   # YandexDiskClient
    db_connection: Any = None    # asyncpg.Connection
    contracts: list[ContractRecord] = field(default_factory=list)
    _audit_log: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            self.name = "Макс"
        if not self.codename:
            self.codename = "CONTRACT-MGR"
        if not self.role:
            self.role = "Менеджер контрактов"

    async def scan_contracts(self, base_path: str = "Документы НЕКСТАП/АРТИСТЫ") -> list[dict[str, Any]]:
        """Сканирует облачное хранилище на наличие новых/обновлённых контрактов.

        Args:
            base_path: Базовая директория с контрактами.

        Returns:
            Список найденных файлов с мета-информацией.

        Raises:
            RuntimeError: Если storage_client не настроен.
        """
        if self.storage_client is None:
            raise RuntimeError("Storage client not configured")

        files = await self.storage_client.list_files(base_path)
        contracts_found = []

        for f in files:
            name = f.get("name", "")
            if name.endswith((".pdf", ".docx", ".doc")):
                contracts_found.append({
                    "path": f.get("path", ""),
                    "name": name,
                    "type": name.rsplit(".", 1)[-1],
                    "modified": f.get("modified", ""),
                })

        logger.info("Scanned %s: found %d contract files", base_path, len(contracts_found))
        return contracts_found

    def verify_splits(
        self,
        db_splits: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Сравнивает сплиты в БД с данными из контрактов.

        Args:
            db_splits: Текущие сплиты из БД {artist: pct}.

        Returns:
            Список расхождений.
        """
        if db_splits is None:
            db_splits = {}

        mismatches = []
        for contract in self.contracts:
            db_pct = db_splits.get(contract.artist)
            if db_pct is None:
                mismatches.append({
                    "artist": contract.artist,
                    "type": "missing_in_db",
                    "contract_split": contract.split_pct,
                })
            elif abs(db_pct - contract.split_pct) > 0.001:
                mismatches.append({
                    "artist": contract.artist,
                    "type": "mismatch",
                    "contract_split": contract.split_pct,
                    "db_split": db_pct,
                })

        if mismatches:
            logger.warning("Split verification: %d mismatches found", len(mismatches))
        return mismatches

    def check_expirations(self, days_ahead: int = 90) -> list[dict[str, Any]]:
        """Находит контракты, истекающие в ближайшие N дней.

        Args:
            days_ahead: Горизонт проверки (по умолчанию 90 дней).

        Returns:
            Список контрактов, срок которых скоро истекает.
        """
        today = datetime.utcnow().date()
        deadline = today + timedelta(days=days_ahead)
        expiring = []

        for contract in self.contracts:
            if not contract.expiry_date:
                continue
            try:
                exp = datetime.strptime(contract.expiry_date, "%Y-%m-%d").date()
            except ValueError:
                logger.warning("Bad date format for %s: %s", contract.artist, contract.expiry_date)
                continue

            if exp <= deadline:
                days_left = (exp - today).days
                expiring.append({
                    "artist": contract.artist,
                    "expiry_date": contract.expiry_date,
                    "days_left": days_left,
                    "status": "expired" if days_left <= 0 else "expiring_soon",
                })

        logger.info("Expiration check (%d days): %d contracts flagged", days_ahead, len(expiring))
        return expiring

    def parse_pdf(self, file_path: str) -> dict[str, Any]:
        """Извлекает данные сплита из PDF контракта.

        Args:
            file_path: Путь к PDF файлу.

        Returns:
            Словарь с извлечёнными данными (artist, split, dates).
        """
        # Заглушка для парсинга — в реальности будет PyPDF2/pdfplumber
        logger.info("Parsing PDF: %s", file_path)
        return {
            "source": file_path,
            "format": "pdf",
            "parsed": True,
            "artist": None,
            "split_pct": None,
            "signed_date": None,
            "expiry_date": None,
            "raw_text_length": 0,
        }

    def parse_docx(self, file_path: str) -> dict[str, Any]:
        """Извлекает данные сплита из DOCX шаблона.

        Args:
            file_path: Путь к DOCX файлу.

        Returns:
            Словарь с извлечёнными данными.
        """
        logger.info("Parsing DOCX: %s", file_path)
        return {
            "source": file_path,
            "format": "docx",
            "parsed": True,
            "artist": None,
            "split_pct": None,
            "signed_date": None,
            "expiry_date": None,
        }

    def get_contract_status(self, artist: str) -> dict[str, Any] | None:
        """Полная информация о контракте артиста.

        Args:
            artist: Имя артиста.

        Returns:
            Детали контракта или None.
        """
        for contract in self.contracts:
            if contract.artist == artist:
                return {
                    "artist": contract.artist,
                    "split_pct": contract.split_pct,
                    "signed_date": contract.signed_date,
                    "expiry_date": contract.expiry_date,
                    "file_path": contract.file_path,
                    "file_type": contract.file_type,
                    "status": contract.status,
                    "notes": contract.notes,
                }
        return None

    def update_split(self, artist: str, new_pct: float, reason: str) -> dict[str, Any]:
        """Изменяет сплит артиста с записью в аудит-лог.

        Args:
            artist: Имя артиста.
            new_pct: Новый процент (0.0-1.0).
            reason: Причина изменения.

        Returns:
            Запись об изменении.

        Raises:
            ContractError: Если контракт не найден или процент невалидный.
        """
        if not 0.0 <= new_pct <= 1.0:
            raise ContractError(f"Invalid split percentage: {new_pct}. Must be 0.0-1.0.")

        contract = None
        for c in self.contracts:
            if c.artist == artist:
                contract = c
                break

        if contract is None:
            raise ContractError(f"Contract not found for artist: {artist}")

        old_pct = contract.split_pct
        contract.split_pct = new_pct

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "artist": artist,
            "old_split": old_pct,
            "new_split": new_pct,
            "reason": reason,
            "changed_by": self.name,
        }
        self._audit_log.append(audit_entry)

        logger.info("Split updated for %s: %.0f%% -> %.0f%% (%s)", artist, old_pct * 100, new_pct * 100, reason)
        return audit_entry

    def generate_summary(self) -> dict[str, Any]:
        """Сводка по всем контрактам лейбла."""
        active = [c for c in self.contracts if c.status == "active"]
        expired = [c for c in self.contracts if c.status == "expired"]
        placeholders = [c for c in self.contracts if c.status == "placeholder"]

        return {
            "total": len(self.contracts),
            "active": len(active),
            "expired": len(expired),
            "placeholders": len(placeholders),
            "average_split": (
                sum(c.split_pct for c in active) / len(active)
                if active else 0
            ),
            "artists_with_files": len([c for c in self.contracts if c.file_path]),
            "audit_log_entries": len(self._audit_log),
        }

    def add_contract(self, contract: ContractRecord) -> None:
        """Добавляет контракт в реестр."""
        self.contracts.append(contract)
        logger.info("Contract added for %s (split=%.0f%%)", contract.artist, contract.split_pct * 100)
