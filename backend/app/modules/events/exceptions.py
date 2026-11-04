"""Event-specific domain exceptions."""

from ..common.exceptions import DomainError


class InvalidEventError(DomainError):
    def __init__(self, message: str, error_code: str = "INVALID_EVENT"):
        super().__init__(message, error_code)


class SourceNotFoundError(DomainError):
    def __init__(self, source_id: str):
        super().__init__(
            f"Production source '{source_id}' not found",
            "SOURCE_NOT_FOUND",
        )
