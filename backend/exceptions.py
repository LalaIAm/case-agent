"""
Custom exception classes for the Minnesota Conciliation Court Case Agent API.
Each exception includes status code, detail message, and optional metadata for consistent error responses.
"""
from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception for application errors with HTTP status and structured details."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type or self.__class__.__name__
        self.details = details or {}


class CaseNotFoundError(AppException):
    """Raised when a case is not found."""

    def __init__(self, message: str = "Case not found", case_id: Optional[str] = None, **kwargs: Any) -> None:
        details = kwargs.pop("details", None) or ({"case_id": case_id} if case_id else {})
        super().__init__(message, status_code=404, error_type="CaseNotFoundError", details=details, **kwargs)


class DocumentNotFoundError(AppException):
    """Raised when a document is not found."""

    def __init__(
        self,
        message: str = "Document not found",
        document_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", None) or ({"document_id": document_id} if document_id else {})
        super().__init__(message, status_code=404, error_type="DocumentNotFoundError", details=details, **kwargs)


class AgentRunNotFoundError(AppException):
    """Raised when an agent run is not found."""

    def __init__(
        self,
        message: str = "Agent run not found",
        run_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", None) or ({"run_id": run_id} if run_id else {})
        super().__init__(message, status_code=404, error_type="AgentRunNotFoundError", details=details, **kwargs)


class SessionNotFoundError(AppException):
    """Raised when a session is not found (or no active session)."""

    def __init__(
        self,
        message: str = "Session not found",
        session_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", None) or ({"session_id": session_id} if session_id else {})
        super().__init__(message, status_code=404, error_type="SessionNotFoundError", details=details, **kwargs)


class UnauthorizedError(AppException):
    """Raised when the user is not authorized to perform the action."""

    def __init__(self, message: str = "Not authorized to access this resource", **kwargs: Any) -> None:
        super().__init__(message, status_code=403, error_type="UnauthorizedError", **kwargs)


class ValidationError(AppException):
    """Raised when request validation fails (beyond Pydantic)."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=422, error_type="ValidationError", details=details or {}, **kwargs)


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Too many requests",
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", None) or ({"retry_after": retry_after} if retry_after is not None else {})
        super().__init__(message, status_code=429, error_type="RateLimitError", details=details, **kwargs)


class AgentExecutionError(AppException):
    """Raised when an agent execution fails."""

    def __init__(
        self,
        message: str = "Agent execution failed",
        agent_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        d = details or {}
        if agent_name is not None:
            d["agent_name"] = agent_name
        super().__init__(message, status_code=500, error_type="AgentExecutionError", details=d, **kwargs)
