"""
AI Model Lifecycle Domain Models
Defines lifecycle state machine, request priority queuing schemas, and runtime instance descriptors.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from ai.core.contracts import ModelProvenance
from ai.hardware.fit_engine import HardwareFitResult
from ai.registry.models import ModelTaskTypeEnum


class LifecycleStateEnum(str, Enum):
    """Formal Model Lifecycle State Machine Enum."""
    REGISTERED = "REGISTERED"
    PREFLIGHT = "PREFLIGHT"
    LOADING = "LOADING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    CANCELLING = "CANCELLING"
    UNLOADING = "UNLOADING"
    RELEASED = "RELEASED"

    # Terminal / Failure States
    LOAD_FAILED = "LOAD_FAILED"
    HEALTH_DEGRADED = "HEALTH_DEGRADED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    OOM_RECOVERED = "OOM_RECOVERED"
    QUARANTINED_RUNTIME = "QUARANTINED_RUNTIME"


class RequestPriorityEnum(int, Enum):
    """Request Priority Ordering: Higher integer represents higher execution priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3


class QueuedRequestStatusEnum(str, Enum):
    """Queue Request Lifecycle Status."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    FAILED = "FAILED"


class RuntimeInstance(BaseModel):
    """Descriptor for an active, resident, or transitioning model runtime instance."""
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str
    task_type: ModelTaskTypeEnum = ModelTaskTypeEnum.GENERATION
    state: LifecycleStateEnum = LifecycleStateEnum.REGISTERED
    pid: Optional[int] = None
    loaded_at: Optional[str] = None
    last_active_at: Optional[str] = None
    context_length: int = 4096
    gpu_layers: int = 0
    estimated_vram_mb: float = 0.0
    estimated_ram_mb: float = 0.0
    observed_vram_mb: float = 0.0
    observed_ram_mb: float = 0.0
    fit_result: Optional[HardwareFitResult] = None
    provenance: Optional[ModelProvenance] = None
    last_error: Optional[str] = None
    health_check_passed: bool = False

    def update_state(self, new_state: LifecycleStateEnum, error_message: Optional[str] = None) -> None:
        """Transitions instance to new lifecycle state."""
        self.state = new_state
        self.last_active_at = datetime.now(timezone.utc).isoformat()
        if error_message:
            self.last_error = error_message


class QueuedInferenceRequest(BaseModel):
    """Representation of an inference invocation waiting in the sequential queue."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str
    task_type: ModelTaskTypeEnum = ModelTaskTypeEnum.GENERATION
    priority: RequestPriorityEnum = RequestPriorityEnum.NORMAL
    prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    max_tokens: int = 512
    temperature: float = 0.0
    timeout_seconds: float = 60.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: QueuedRequestStatusEnum = QueuedRequestStatusEnum.QUEUED
    error: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}
