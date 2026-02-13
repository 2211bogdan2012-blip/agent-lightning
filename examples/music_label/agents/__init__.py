"""Music Label AI Agent Framework — переиспользуемые агенты для любого лейбла."""
from .base_agent import BaseAgent, TelegramCommand, AgentTask
from .presets import create_all_agents, create_director, create_royalty_manager
from .presets import create_contract_manager, create_release_manager
from .presets import create_analytics, create_devops

__all__ = [
    "BaseAgent", "TelegramCommand", "AgentTask",
    "create_all_agents", "create_director", "create_royalty_manager",
    "create_contract_manager", "create_release_manager",
    "create_analytics", "create_devops",
]
