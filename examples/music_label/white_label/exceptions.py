"""Custom exceptions for the white-label framework."""


class WhiteLabelError(Exception):
    """Base exception for white-label framework."""


class ConfigurationError(WhiteLabelError):
    """Invalid or incomplete configuration."""


class DistributorError(WhiteLabelError):
    """Error communicating with a distributor API."""


class AuthenticationError(DistributorError):
    """Failed to authenticate with a service."""


class StorageError(WhiteLabelError):
    """Error accessing contract storage."""


class HostingError(WhiteLabelError):
    """Error with hosting provider operations."""


class MigrationError(WhiteLabelError):
    """Error during distributor migration."""
