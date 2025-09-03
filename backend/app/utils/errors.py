"""Small error helpers so every failure is returned as clean JSON."""
from __future__ import annotations


class ApiError(Exception):
    """Raise anywhere in a route/service to return `{error, message}` with a status code."""

    def __init__(self, message: str, status: int = 400, code: str = "bad_request"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
