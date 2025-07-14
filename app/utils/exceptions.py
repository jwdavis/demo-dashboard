"""
Custom exceptions for Success HQ application.

This module defines application-specific exceptions for better error handling
and more precise error reporting.
"""


class SuccessHQError(Exception):
    """Base exception for Success HQ application."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(SuccessHQError):
    """Database-related errors."""

    pass


class ValidationError(SuccessHQError):
    """Input validation errors."""

    pass


class ConfigurationError(SuccessHQError):
    """Configuration-related errors."""

    pass


class ExternalServiceError(SuccessHQError):
    """External service (BigQuery, etc.) errors."""

    pass


class AuthenticationError(SuccessHQError):
    """Authentication-related errors."""

    pass


class AuthorizationError(SuccessHQError):
    """Authorization-related errors."""

    pass
