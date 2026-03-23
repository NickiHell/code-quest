"""Domain-level errors (framework-agnostic)."""


class DomainError(Exception):
    """Base class for business rule violations."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when an aggregate or entity cannot be located."""


class DomainValidationError(DomainError):
    """Raised when input violates domain constraints."""


class ExternalServiceError(DomainError):
    """Raised when an outbound dependency (AI, sandbox) fails."""
