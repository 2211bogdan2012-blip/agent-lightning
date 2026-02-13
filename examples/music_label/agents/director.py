"""
Director Agent — AI-директор лейбла (NEXUS).

Координирует работу всех агентов, маршрутизирует задачи,
принимает стратегические решения, обрабатывает Telegram-команды.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base_agent import BaseAgent, AgentTask

logger = logging.getLogger(__name__)

# Ключевые слова для маршрутизации задач к агентам
ROUTING_RULES: dict[str, list[str]] = {
    "ROYALTY-ENGINE": [
        "роялти", "royalty", "выплат", "сплит", "split", "аванс",
        "advance", "отчёт", "report", "баланс", "balance", "payout",
        "koala", "fetch", "расчёт",
    ],
    "CONTRACT-MGR": [
        "контракт", "contract", "договор", "сплит", "split", "срок",
        "expir", "подписа", "sign", "юрид", "legal", "yandex", "диск",
    ],
    "RELEASE-PIPE": [
        "релиз", "release", "трек", "track", "альбом", "album",
        "сингл", "single", "площад", "dsp", "isrc", "upc", "artwork",
    ],
    "ANALYTICS-AI": [
        "аналитик", "analytic", "тренд", "trend", "стрим", "stream",
        "статистик", "stats", "дайджест", "digest", "прогноз", "forecast",
    ],
    "DEVOPS-BOT": [
        "деплой", "deploy", "бэкап", "backup", "health", "лог", "log",
        "ci", "cd", "docker", "render", "сервер", "server", "scale",
    ],
}

# Приоритеты по типу задачи
PRIORITY_WEIGHTS: dict[str, int] = {
    "urgent": 100,
    "financial": 80,
    "legal": 70,
    "release": 60,
    "analytics": 40,
    "maintenance": 30,
    "info": 10,
}


@dataclass
class EscalationRule:
    """Правило эскалации проблемы."""
    from_agent: str
    condition: str
    action: str  # notify_admin | auto_resolve | block


@dataclass
class Director(BaseAgent):
    """AI-директор лейбла. Координирует всех агентов."""

    task_queue: list[AgentTask] = field(default_factory=list)
    agents: dict[str, BaseAgent] = field(default_factory=dict)
    escalation_rules: list[EscalationRule] = field(default_factory=list)
    _decision_log: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            self.name = "NEXUS"
        if not self.codename:
            self.codename = "DIRECTOR"
        if not self.role:
            self.role = "AI-директор лейбла"
        if not self.escalation_rules:
            self.escalation_rules = [
                EscalationRule("ROYALTY-ENGINE", "error_in_calculation", "notify_admin"),
                EscalationRule("CONTRACT-MGR", "split_mismatch", "block"),
                EscalationRule("DEVOPS-BOT", "deploy_failed", "notify_admin"),
            ]

    def register_agent(self, agent: BaseAgent) -> None:
        """Регистрирует агента в команде."""
        self.agents[agent.codename] = agent
        logger.info("Agent registered: %s (%s)", agent.name, agent.codename)

    def delegate(self, task: AgentTask) -> str | None:
        """Маршрутизирует задачу к подходящему агенту.

        Анализирует текст задачи и находит агента с максимальным
        совпадением ключевых слов.

        Returns:
            Codename агента или None, если не найден.
        """
        text_lower = task.text.lower()
        scores: dict[str, int] = {}

        for codename, keywords in ROUTING_RULES.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[codename] = score

        if not scores:
            logger.warning("No agent matched for task: %s", task.text[:80])
            return None

        best = max(scores, key=scores.get)  # type: ignore[arg-type]

        self._decision_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "delegate",
            "task": task.text[:120],
            "routed_to": best,
            "scores": scores,
        })

        task.status = "active"
        if best in self.agents:
            self.agents[best].tasks.append(task)

        logger.info("Task delegated to %s (score=%d): %s", best, scores[best], task.text[:60])
        return best

    def prioritize(self, tasks: list[AgentTask]) -> list[AgentTask]:
        """Сортирует задачи по приоритету.

        Учитывает тип задачи (urgent/financial/legal/...) и наличие
        дедлайна в тексте.
        """

        def _score(t: AgentTask) -> int:
            text = t.text.lower()
            score = 0
            for keyword, weight in PRIORITY_WEIGHTS.items():
                if keyword in text:
                    score = max(score, weight)
            # Бонус за наличие дедлайна
            if any(word in text for word in ("срочно", "urgent", "deadline", "дедлайн", "asap")):
                score += 50
            return score

        return sorted(tasks, key=_score, reverse=True)

    def escalate(self, issue: str, from_agent: str) -> dict[str, str]:
        """Обрабатывает эскалацию от агента.

        Returns:
            Словарь с action и message.
        """
        for rule in self.escalation_rules:
            if rule.from_agent == from_agent and rule.condition in issue.lower():
                self._decision_log.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "escalation",
                    "from": from_agent,
                    "issue": issue[:120],
                    "rule_action": rule.action,
                })
                return {
                    "action": rule.action,
                    "message": f"Escalation from {from_agent}: {issue}",
                }

        # Дефолтное поведение — уведомить администратора
        return {
            "action": "notify_admin",
            "message": f"Unmatched escalation from {from_agent}: {issue}",
        }

    def status_report(self) -> dict[str, Any]:
        """Агрегирует статус всех агентов в один отчёт."""
        report: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "director": self.name,
            "agents_count": len(self.agents),
            "queue_length": len(self.task_queue),
            "agents": {},
        }

        for codename, agent in self.agents.items():
            pending = [t for t in agent.tasks if t.status == "pending"]
            active = [t for t in agent.tasks if t.status == "active"]
            done = [t for t in agent.tasks if t.status == "done"]
            report["agents"][codename] = {
                "name": agent.name,
                "role": agent.role,
                "status": agent.status,
                "tasks_pending": len(pending),
                "tasks_active": len(active),
                "tasks_done": len(done),
            }

        return report

    def quarterly_review(self, quarter: str | None = None) -> dict[str, Any]:
        """Генерирует квартальный бизнес-обзор.

        Args:
            quarter: Квартал (напр. "Q4 2025"). Если None — текущий.
        """
        now = datetime.utcnow()
        if quarter is None:
            q = (now.month - 1) // 3 + 1
            quarter = f"Q{q} {now.year}"

        review: dict[str, Any] = {
            "quarter": quarter,
            "generated_at": now.isoformat(),
            "team_size": len(self.agents),
            "total_decisions": len(self._decision_log),
            "sections": {
                "overview": f"Quarterly review for {quarter}",
                "agents_summary": {
                    codename: {
                        "name": agent.name,
                        "tasks_completed": len([t for t in agent.tasks if t.status == "done"]),
                    }
                    for codename, agent in self.agents.items()
                },
                "escalations": [
                    entry for entry in self._decision_log
                    if entry.get("action") == "escalation"
                ],
            },
        }
        return review

    def handle_telegram(self, message: str, user_id: int | None = None) -> str:
        """Обрабатывает Telegram-команду.

        Args:
            message: Текст сообщения (напр. "/status").
            user_id: Telegram ID отправителя.

        Returns:
            Текстовый ответ для отправки в Telegram.
        """
        parts = message.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if command == "/help":
            lines = ["<b>Доступные команды:</b>"]
            for agent in self.agents.values():
                for cmd in agent.commands:
                    admin_tag = " (admin)" if cmd.admin_only else ""
                    lines.append(f"  <code>{cmd.command}</code> -- {cmd.description}{admin_tag}")
            return "\n".join(lines)

        if command == "/status":
            report = self.status_report()
            lines = [f"<b>Статус лейбла</b> ({report['timestamp'][:10]})"]
            for codename, info in report["agents"].items():
                lines.append(
                    f"  {info['name']} ({codename}): "
                    f"pending={info['tasks_pending']}, "
                    f"active={info['tasks_active']}, "
                    f"done={info['tasks_done']}"
                )
            return "\n".join(lines)

        if command == "/team":
            lines = [f"<b>AI-команда ({len(self.agents)} агентов):</b>"]
            for codename, agent in self.agents.items():
                lines.append(f"  {agent.avatar} {agent.name} -- {agent.role} [{agent.status}]")
            return "\n".join(lines)

        # Для неизвестных команд — попробовать маршрутизировать как задачу
        task = AgentTask(text=message)
        target = self.delegate(task)
        if target:
            agent_name = self.agents[target].name if target in self.agents else target
            return f"Задача направлена агенту {agent_name} ({target})."

        return "Команда не распознана. Используй /help для списка команд."
