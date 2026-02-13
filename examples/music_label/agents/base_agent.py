"""
Base Agent — Базовый класс AI-сотрудника музыкального лейбла.

Каждый агент наследует BaseAgent и получает:
- Имя, роль, модель, инструменты
- Персональную память (контекст)
- Генерацию SOUL.md для OpenClaw
- Генерацию Telegram-команд
- Сериализацию в JSON для хранения

Пример:
    agent = BaseAgent(
        name="Rita",
        codename="ROYALTY-ENGINE",
        role="Менеджер по роялти",
        model="opus",
        tools=["Koala Music API", "PostgreSQL"],
        memory=["Сплиты 30 артистов", "Q4 2025 данные"],
    )
    soul_md = agent.generate_soul_md(label_name="НЕКСТ АП")
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import os


@dataclass
class AgentTask:
    """Задача, назначенная агенту."""
    text: str
    status: str = "pending"  # pending | active | done | blocked


@dataclass
class TelegramCommand:
    """Telegram-команда агента."""
    command: str       # /report, /balance, etc.
    description: str   # Описание на русском
    admin_only: bool = False


@dataclass
class BaseAgent:
    """Базовый AI-сотрудник музыкального лейбла."""
    
    name: str                          # Человеческое имя: "Рита"
    codename: str                      # Кодовое: "ROYALTY-ENGINE"
    role: str                          # "Менеджер по роялти"
    model: str = "opus"                # opus | sonnet | haiku
    avatar: str = "🤖"
    color: str = "#22c955"
    
    # Функционал
    specialty: str = ""
    tools: list = field(default_factory=list)
    memory: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    commands: list = field(default_factory=list)
    
    # Статус
    status: str = "planned"            # active | building | planned
    description: str = ""
    
    # Портируемые настройки
    portable: bool = True              # Может работать на другом лейбле
    requires_api: list = field(default_factory=list)  # Какие API нужны
    
    def generate_soul_md(self, label_name: str, label_info: dict = None) -> str:
        """Генерирует SOUL.md файл для OpenClaw агента.
        
        SOUL.md определяет личность, знания и поведение агента
        в OpenClaw Gateway. Это его "душа" — persistent identity.
        """
        info = label_info or {}
        artists_count = info.get("artists_count", "N")
        
        soul = f"""# {self.name} ({self.codename})
## {self.role} — {label_name}

Ты — {self.name}, {self.role} музыкального лейбла {label_name}.
Твоё кодовое имя: {self.codename}. Модель: Claude {self.model.title()}.

## Твоя зона ответственности
{self.specialty}

## Описание
{self.description}

## Инструменты
{chr(10).join(f'- {t}' for t in self.tools)}

## Что ты помнишь (контекст)
{chr(10).join(f'- {m}' for m in self.memory)}

## Правила поведения
- Отвечай на русском языке
- Будь конкретным и точным в цифрах
- При ошибках сообщай NEXUS (директору)
- Не выходи за рамки своей зоны ответственности
- Логируй все действия для аудита

## Telegram-команды
{chr(10).join(f'- `{c.command}` — {c.description}{" (admin)" if c.admin_only else ""}' for c in self.commands)}
"""
        return soul.strip()

    def generate_identity_md(self, label_name: str) -> str:
        """Генерирует IDENTITY.md для Telegram-бота."""
        return f"""# {self.name} — {label_name}

**Роль:** {self.role}
**Модель:** Claude {self.model.title()}
**Статус:** {self.status}

{self.description}

## Команды
{chr(10).join(f'`{c.command}` — {c.description}' for c in self.commands)}
"""

    def to_dict(self) -> dict:
        """Сериализация в dict для JSON/YAML хранения."""
        return {
            "name": self.name,
            "codename": self.codename,
            "role": self.role,
            "model": self.model,
            "avatar": self.avatar,
            "status": self.status,
            "specialty": self.specialty,
            "tools": self.tools,
            "memory": self.memory,
            "commands": [
                {"command": c.command, "description": c.description, 
                 "admin_only": c.admin_only}
                for c in self.commands
            ],
            "portable": self.portable,
            "requires_api": self.requires_api,
        }

    def save_soul(self, directory: str, label_name: str, label_info: dict = None):
        """Сохраняет SOUL.md в указанную директорию."""
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "SOUL.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_soul_md(label_name, label_info))
        return path

    @classmethod
    def from_dict(cls, data: dict) -> "BaseAgent":
        """Десериализация из dict."""
        commands = [
            TelegramCommand(**c) for c in data.pop("commands", [])
        ]
        tasks = [
            AgentTask(**t) if isinstance(t, dict) else AgentTask(text=t)
            for t in data.pop("tasks", [])
        ]
        return cls(**data, commands=commands, tasks=tasks)
