# Music Label AI Agent Framework
# Переиспользуемый фреймворк AI-сотрудников для музыкальных лейблов
# Forked from microsoft/agent-lightning

## Что это

Набор готовых AI-агентов для управления музыкальным лейблом. Каждый агент — специализированный работник с памятью, инструментами и зоной ответственности. Фреймворк портируется на любой лейбл за 30 минут.

## Быстрый старт

```bash
# 1. Скопируй шаблон конфигурации
cp label_config.example.yaml label_config.yaml

# 2. Заполни данные лейбла
# - название, артисты, контракты, API ключи

# 3. Сгенерируй агентов
python generate_agents.py --config label_config.yaml --output ./agents/

# 4. Запусти через OpenClaw или Claude Code Agent Teams
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude
```

## Архитектура

```
┌─────────────────────────────────────────────┐
│              DIRECTOR (Opus 4.6)             │
│     Координация, стратегия, общение          │
├──────┬──────┬──────┬──────┬────────┤
│ RITA │ MAX  │ LENA │DENIS │ SASHA  │
│роялти│контр.│релизы│анал. │ devops │
│Opus  │Opus  │Sonn. │Sonn. │ Sonn.  │
└──────┴──────┴──────┴──────┴────────┘
```

## Агенты

| Агент | Роль | Модель | Инструменты | Портируемость |
|-------|------|--------|-------------|--------------|
| Director | Координация всех процессов | Opus 4.6 | Telegram, WhatsApp, все модули | Универсальный |
| Rita | Расчёт роялти, отчёты | Opus 4.5 | Koala API, PostgreSQL, PDF | Любой дистрибьютор |
| Max | Контракты, юридическое | Opus 4.5 | Яндекс.Диск, PDF Parser, БД | Любой лейбл |
| Lena | Релизы, дистрибуция | Sonnet 4.5 | Koala Portal, DSP APIs | Любой дистрибьютор |
| Denis | Аналитика, тренды | Sonnet 4.5 | OLAP, Charts, Streaming APIs | Универсальный |
| Sasha | DevOps, мониторинг | Sonnet 4.5 | Docker, Render, GitHub Actions | Универсальный |

## Портирование на другой лейбл

1. Скопируй `label_config.example.yaml` → `label_config.yaml`
2. Замени `label_name`, `artists`, `distributor`, `api_keys`
3. Запусти `python generate_agents.py` — сгенерирует SOUL.md для каждого агента
4. Настрой Telegram-бота через BotFather
5. Готово — 6 AI-сотрудников работают на новый лейбл

## Файлы

```
music_label/
├── README.md              # Этот файл
├── label_config.example.yaml  # Шаблон конфигурации лейбла
├── generate_agents.py     # Генератор агентов из конфига
├── agents/
│   ├── base_agent.py      # Базовый класс агента
│   ├── director.py        # Директор (NEXUS)
│   ├── royalty_manager.py # Менеджер роялти (Rita)
│   ├── contract_manager.py# Менеджер контрактов (Max)
│   ├── release_manager.py # Релиз-менеджер (Lena)
│   ├── analytics.py       # Аналитик (Denis)
│   └── devops.py          # DevOps (Sasha)
├── templates/
│   ├── SOUL.md.j2         # Шаблон SOUL.md для OpenClaw
│   ├── IDENTITY.md.j2     # Шаблон для Telegram-бота
│   └── telegram_commands.j2 # Шаблон команд
├── integrations/
│   ├── koala_music.py     # Клиент Koala Music API
│   ├── yandex_disk.py     # Парсер Яндекс.Диска
│   ├── telegram_notify.py # Уведомления в Telegram
│   └── render_deploy.py   # Авто-деплой на Render
└── tests/
    └── test_agents.py     # Тесты фреймворка
```

## Лицензия

MIT — используйте свободно для любого лейбла.
