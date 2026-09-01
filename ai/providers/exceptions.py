"""
Provider Adapter Layer Typed Exception Hierarchy
Preserves provider name, task type, error classification, retryability, fallback policy, and diagnostics.
"""

from typing import Any, Dict, Optional
from ai.core.contracts import TaskType


class AIProviderError(Exception):
    """Base exception for all Provider Adapter operations."""

    def __init__(
        self,
        message: str,
        provider_name: str,
        task_type: Optional[TaskType] = None,
        model_id: Optional[str] = None,
        error_class: str = "PROVIDER_ERROR",
        original_error_type: Optional[str] = None,
        retryable: bool = False,
        fallback_allowed: bool = True,
        diagnostic_details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider_name = provider_name
        self.task_type = task_type
        self.model_id = model_id
        self.error_class = error_class
        self.original_error_type = original_error_type
        self.retryable = retryable
        self.fallback_allowed = fallback_allowed
        self.diagnostic_details = diagnostic_details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "provider_name": self.provider_name,
            "task_type": self.task_type.value if self.task_type else None,
            "model_id": self.model_id,
            "error_class": self.error_class,
            "original_error_type": self.original_error_type,
            "retryable": self.retryable,
            "fallback_allowed": self.fallback_allowed,
            "diagnostic_details": self.diagnostic_details,
        }


class ProviderUnavailableError(AIProviderError):
    """Raised when a local daemon/endpoint (e.g. Ollama, LM Studio) cannot be connected to."""

    def __init__(self, message: str, provider_name: str, **kwargs: Any):
        super().__init__(
            message=message,
            provider_name=provider_name,
            error_class="PROVIDER_UNAVAILABLE",
            retryable=True,
            fallback_allowed=True,
            **kwargs,
        )


class ModelNotFoundError(AIProviderError):
    """Raised when the requested model is not loaded or missing in the target provider."""

    def __init__(self, message: str, provider_name: str, model_id: Optional[str] = None, **kwargs: Any):
        super().__init__(
            message=message,
            provider_name=provider_name,
            model_id=model_id,
            error_class="MODEL_NOT_FOUND",
            retryable=False,
            fallback_allowed=True,
            **kwargs,
        )


class ProviderTimeoutError(AIProviderError):
    """Raised when provider inference exceeds the configured deadline."""

    def __init__(self, message: str, provider_name: str, timeout_seconds: float, **kwargs: Any):
        details = kwargs.pop("diagnostic_details", {})
        details["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            provider_name=provider_name,
            error_class="PROVIDER_TIMEOUT",
            retryable=True,
            fallback_allowed=True,
            diagnostic_details=details,
            **kwargs,
        )


class ProviderOOMError(AIProviderError):
    """Raised when provider triggers an Out-Of-Memory condition on VRAM or RAM."""

    def __init__(self, message: str, provider_name: str, **kwargs: Any):
        super().__init__(
            message=message,
            provider_name=provider_name,
            error_class="PROVIDER_OOM",
            retryable=False,
            fallback_allowed=True,
            **kwargs,
        )


class ProviderCrashedError(AIProviderError):
    """Raised when underlying server process terminates unexpectedly."""

    def __init__(self, message: str, provider_name: str, exit_code: Optional[int] = None, **kwargs: Any):
        details = kwargs.pop("diagnostic_details", {})
        if exit_code is not None:
            details["exit_code"] = exit_code
        super().__init__(
            message=message,
            provider_name=provider_name,
            error_class="PROVIDER_CRASHED",
            retryable=True,
            fallback_allowed=True,
            diagnostic_details=details,
            **kwargs,
        )


class ContextOverflowError(AIProviderError):
    """Raised when prompt + generation exceeds provider or model context length limit."""

    def __init__(self, message: str, provider_name: str, context_limit: int, requested_tokens: int, **kwargs: Any):
        details = kwargs.pop("diagnostic_details", {})
        details["context_limit"] = context_limit
        details["requested_tokens"] = requested_tokens
        super().__init__(
            message=message,
            provider_name=provider_name,
            error_class="CONTEXT_OVERFLOW",
            retryable=False,
            fallback_allowed=False,
            diagnostic_details=details,
            **kwargs,
        )


class ProviderModelIncompatibleError(AIProviderError):
    """Raised when a model is architecturally or functionally incompatible with the provider."""

    def __init__(self, message: str, provider_name: str, model_id: Optional[str] = None, **kwargs: Any):
        super().__init__(
            message=message,
            provider_name=provider_name,
            model_id=model_id,
            error_class="PROVIDER_MODEL_INCOMPATIBLE",
            retryable=False,
            fallback_allowed=True,
            **kwargs,
        )


class InputValidationError(AIProviderError):
    """Raised when input parameters fail schema or semantic validation."""

    def __init__(self, message: str, provider_name: str, **kwargs: Any):
        super().__init__(
            message=message,
            provider_name=provider_name,
            error_class="INPUT_VALIDATION_ERROR",
            retryable=False,
            fallback_allowed=False,
            **kwargs,
        )
