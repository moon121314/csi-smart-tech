"""Base domain-level exceptions."""


class DomainError(Exception):
    """Base class for all domain errors. Maps to REJECTED in the API layer."""

    def __init__(self, message: str, error_code: str = "DOMAIN_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
