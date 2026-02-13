"""White-label framework for music label AI agents."""

from .configurator import LabelConfigurator
from .migration import DistributorMigrator

__all__ = ["LabelConfigurator", "DistributorMigrator"]
