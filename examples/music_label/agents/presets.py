"""
Предустановленные AI-агенты музыкального лейбла.

Каждая функция возвращает готового BaseAgent с командами, инструментами и памятью.
Для портирования на другой лейбл достаточно вызвать generate_agents.py с новым конфигом —
эти шаблоны адаптируются автоматически через label_config.yaml.
"""

from .base_agent import BaseAgent, TelegramCommand


def create_director(label_name: str, artists_count: int = 30) -> BaseAgent:
    return BaseAgent(
        name="NEXUS",
        codename="DIRECTOR",
        role="AI-директор лейбла",
        model="opus",
        avatar="🧠",
        color="#a78bfa",
        status="active",
        specialty="Координация всех AI-агентов, стратегические решения, общение с артистами и партнёрами",
        description=f"Главный AI-агент лейбла {label_name}. Управляет командой из 5 специализированных агентов, "
                    f"принимает стратегические решения, координирует расчёты роялти, контракты и релизы для {artists_count} артистов.",
        tools=["Telegram Bot API", "WhatsApp API", "OpenClaw Gateway", "PostgreSQL", "GitHub API"],
        memory=[
            f"Полная картина лейбла: {artists_count} артистов",
            "Текущие контракты и финансовое состояние",
            "Приоритеты на текущий квартал",
            "История всех решений и изменений",
        ],
        commands=[
            TelegramCommand("/help", "Справка по всем командам"),
            TelegramCommand("/status", "Общий статус лейбла", admin_only=True),
            TelegramCommand("/team", "Статус AI-команды", admin_only=True),
        ],
        portable=True,
        requires_api=["telegram"],
    )


def create_royalty_manager(label_name: str, distributor: str = "Koala Music") -> BaseAgent:
    return BaseAgent(
        name="Рита",
        codename="ROYALTY-ENGINE",
        role="Менеджер по роялти",
        model="opus",
        avatar="💰",
        color="#22c955",
        status="active",
        specialty="Расчёт квартальных выплат, генерация PDF/XLSX отчётов, учёт авансов и сплитов",
        description=f"Рассчитывает роялти для всех артистов {label_name}. Получает данные из {distributor}, "
                    "применяет индивидуальные сплиты (60-80%), учитывает авансы, генерирует персональные отчёты.",
        tools=[
            f"{distributor} API — данные о стримах и доходах",
            "PostgreSQL — payouts, advances, koala_quarterly, split_history",
            "calculator.py — движок расчёта роялти",
            "report_gen.py — PDF с графиками (fpdf2 + matplotlib)",
            "report_xlsx.py — Excel для администрации (openpyxl)",
        ],
        memory=[
            "Сплиты всех артистов с историей изменений",
            "Активные авансы и остатки по каждому артисту",
            "Данные из дистрибьютора по кварталам",
            "Коллаб-маппинги (кто с кем записывал треки)",
        ],
        commands=[
            TelegramCommand("/report", "PDF-отчёт артиста за квартал"),
            TelegramCommand("/royalty Q4 2025", "Расчёт выплат за квартал", admin_only=True),
            TelegramCommand("/report_xlsx Q4 2025", "Excel-отчёт", admin_only=True),
            TelegramCommand("/advances", "Активные авансы", admin_only=True),
            TelegramCommand("/fetch", "Загрузить данные из дистрибьютора", admin_only=True),
        ],
        portable=True,
        requires_api=["distributor", "postgresql"],
    )


def create_contract_manager(label_name: str, storage: str = "yandex_disk") -> BaseAgent:
    return BaseAgent(
        name="Макс",
        codename="CONTRACT-MGR",
        role="Менеджер контрактов",
        model="opus",
        avatar="📋",
        color="#f59e0b",
        status="building",
        specialty="CRUD контрактов, контроль сплитов, мониторинг сроков, привязка файлов договоров",
        description=f"Управляет всеми договорами лейбла {label_name}. Парсит контракты из {storage}, "
                    "следит за сроками действия, контролирует соответствие сплитов.",
        tools=[
            f"{storage} API — хранилище контрактов",
            "PDF Parser — извлечение данных из договоров",
            "PostgreSQL — contracts, artists, split_history",
            "Telegram Notifications — уведомления об истечении",
        ],
        memory=[
            "Реестр всех контрактов с привязкой к файлам",
            "Сплиты по источнику: DOCX, PDF, Excel, 360-deal",
            "Плейсхолдеры (артисты без подтверждённого сплита)",
            "Даты истечения контрактов",
        ],
        commands=[
            TelegramCommand("/contracts", "Сводка контрактов", admin_only=True),
            TelegramCommand("/contracts ARTIST", "Контракты артиста", admin_only=True),
            TelegramCommand("/split ARTIST", "История сплитов", admin_only=True),
            TelegramCommand("/split ARTIST 80", "Установить сплит", admin_only=True),
        ],
        portable=True,
        requires_api=["cloud_storage", "postgresql"],
    )


def create_release_manager(label_name: str, distributor: str = "Koala Music") -> BaseAgent:
    return BaseAgent(
        name="Лена",
        codename="RELEASE-PIPE",
        role="Релиз-менеджер",
        model="sonnet",
        avatar="🎵",
        color="#06b6d4",
        status="planned",
        specialty="Планирование релизов, загрузка на площадки, мониторинг статусов",
        description=f"Управляет всем релизным пайплайном {label_name} через {distributor}. "
                    "Планирует даты выхода, готовит метаданные, отслеживает статусы на всех DSP.",
        tools=[
            f"{distributor} Portal — управление релизами",
            "Spotify for Artists / Apple Music Connect",
            "Release Calendar — график выходов",
            "Telegram — уведомления артистам",
        ],
        memory=[
            "Каталог релизов лейбла",
            "График выходов на месяц вперёд",
            "Статусы на каждой платформе",
            "Требования дистрибьюторов к метаданным",
        ],
        commands=[
            TelegramCommand("/releases", "Список релизов"),
            TelegramCommand("/release_status", "Статусы на площадках", admin_only=True),
            TelegramCommand("/new_release", "Создать новый релиз", admin_only=True),
        ],
        portable=True,
        requires_api=["distributor", "streaming_platforms"],
    )


def create_analytics(label_name: str) -> BaseAgent:
    return BaseAgent(
        name="Денис",
        codename="ANALYTICS-AI",
        role="Аналитик",
        model="sonnet",
        avatar="📊",
        color="#8b5cf6",
        status="planned",
        specialty="Анализ стримов, доходов, трендов. QoQ сравнения, рекомендации по продвижению",
        description=f"Анализирует все данные {label_name}: стримы, доходы, географию, платформы. "
                    "Выявляет тренды, делает QoQ сравнения, даёт рекомендации по продвижению.",
        tools=[
            "OLAP API дистрибьютора — сырые данные",
            "PostgreSQL — исторические данные",
            "matplotlib/seaborn — графики и визуализации",
            "Telegram — еженедельные дайджесты",
        ],
        memory=[
            "Исторические данные по всем кварталам",
            "Тренды по каждому артисту",
            "Бенчмарки по платформам",
            "Результаты прошлых промо-кампаний",
        ],
        commands=[
            TelegramCommand("/stats", "Общая статистика"),
            TelegramCommand("/balance", "Баланс лейбла", admin_only=True),
            TelegramCommand("/trends", "Тренды по артистам", admin_only=True),
            TelegramCommand("/digest", "Еженедельный дайджест", admin_only=True),
        ],
        portable=True,
        requires_api=["distributor_olap", "postgresql"],
    )


def create_devops(label_name: str, hosting: str = "render") -> BaseAgent:
    return BaseAgent(
        name="Саша",
        codename="DEVOPS-BOT",
        role="DevOps-инженер",
        model="sonnet",
        avatar="⚙️",
        color="#ef4444",
        status="building",
        specialty="CI/CD, Docker, деплой, мониторинг, бэкапы, health-check",
        description=f"Обеспечивает инфраструктуру {label_name}: Docker-контейнеры, деплой на {hosting}, "
                    "CI/CD через GitHub Actions, мониторинг и бэкапы PostgreSQL.",
        tools=[
            "Docker — сборка и запуск контейнеров",
            f"{hosting} API — управление деплоем",
            "GitHub Actions — CI/CD pipeline",
            "PostgreSQL — бэкапы и восстановление",
            "aiohttp — health-сервер",
        ],
        memory=[
            f"Конфигурация {hosting} (env vars, instance type)",
            "Dockerfile и зависимости",
            "Ограничения тарифа (sleep, health endpoint)",
            "Логи деплоев и ошибок",
        ],
        commands=[
            TelegramCommand("/deploy", "Запустить деплой", admin_only=True),
            TelegramCommand("/health", "Проверить статус", admin_only=True),
            TelegramCommand("/logs", "Последние логи", admin_only=True),
            TelegramCommand("/backup", "Запустить бэкап", admin_only=True),
        ],
        portable=True,
        requires_api=["docker", "hosting_provider", "github"],
    )


def create_all_agents(label_name: str, config: dict = None) -> list:
    """Создаёт полную команду из 6 агентов на основе конфигурации лейбла."""
    cfg = config or {}
    distributor = cfg.get("distributor", {}).get("name", "Koala Music")
    storage = cfg.get("contracts_storage", {}).get("type", "yandex_disk")
    hosting = cfg.get("hosting", {}).get("provider", "render")
    artists = cfg.get("artists", [])
    
    return [
        create_director(label_name, len(artists) or 30),
        create_royalty_manager(label_name, distributor),
        create_contract_manager(label_name, storage),
        create_release_manager(label_name, distributor),
        create_analytics(label_name),
        create_devops(label_name, hosting),
    ]
