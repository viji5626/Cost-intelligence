"""
Tool Security & Execution Models (AI-11)
Defines sandboxed tool definitions, authorization levels, security policies, and cryptographic audit records.
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class ToolAccessModeEnum(str, Enum):
    """Execution access modes permitted for AI tools."""
    READ_ONLY = "READ_ONLY"
    SIMULATION = "SIMULATION"
    ADMIN_HUMAN_ONLY = "ADMIN_HUMAN_ONLY"  # Strictly forbidden for AI execution paths


class ToolSideEffectEnum(str, Enum):
    """Side effect classification."""
    NO_SIDE_EFFECTS = "NO_SIDE_EFFECTS"
    SIMULATION_ONLY = "SIMULATION_ONLY"


class ToolExecutionStatusEnum(str, Enum):
    """Status codes for tool execution."""
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    TIMEOUT = "TIMEOUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    CIRCUIT_BREAKER_TRIPPED = "CIRCUIT_BREAKER_TRIPPED"
    PROHIBITED_ACTION = "PROHIBITED_ACTION"


class ToolDefinition(BaseModel):
    """
    Metadata specification for an allowlisted, sandboxed domain tool.
    """
    tool_id: str = Field(description="Unique tool identifier (e.g. tool-ecn-search-v1)")
    name: str = Field(description="Invocation name (e.g. search_ecn_records)")
    version: str = Field(default="1.0.0", description="Semantic version of tool handler")
    description: str = Field(description="Natural language tool capability description")
    parameters_schema: Dict[str, Any] = Field(description="JSON Schema or Pydantic schema for arguments")
    access_mode: ToolAccessModeEnum = Field(default=ToolAccessModeEnum.READ_ONLY, description="Access mode")
    data_scope: str = Field(default="ENGINEERING_METADATA", description="Data classification scope")
    allowed_roles: List[str] = Field(default_factory=lambda: ["AI_AGENT", "ENGINEER", "VIEWER"], description="Allowed caller roles")
    dry_run_supported: bool = Field(default=True, description="Whether tool supports dry_run mode")
    side_effect_classification: ToolSideEffectEnum = Field(default=ToolSideEffectEnum.NO_SIDE_EFFECTS)
    network_allowed: bool = Field(default=False, description="Whether outbound network calls are allowed")
    filesystem_allowed: bool = Field(default=False, description="Whether filesystem write access is allowed")
    timeout_seconds: float = Field(default=3.0, ge=0.01, le=10.0, description="Execution timeout limit")
    handler: Optional[Callable[..., Any]] = Field(default=None, exclude=True, description="Constrained domain callable")


class ToolExecutionRequest(BaseModel):
    """
    Standard request envelope for invoking a sandboxed domain tool.
    """
    request_id: str = Field(default_factory=lambda: f"req-tool-{int(datetime.now(timezone.utc).timestamp()*1000)}")
    task_id: str = Field(description="Parent task or conversation ID")
    tool_name: str = Field(description="Target tool name to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Typed input arguments")
    caller_role: str = Field(default="AI_AGENT", description="Role of the invoking entity")
    caller_identity: str = Field(default="local-ai-agent", description="Identity of caller")
    intent_description: str = Field(default="", description="Reason for tool invocation")
    dry_run: bool = Field(default=False, description="Whether to execute in non-mutating dry-run mode")
    policy_version: str = Field(default="v1.0-strict", description="Security policy version")


class ToolExecutionAuditRecord(BaseModel):
    """
    Cryptographic, immutable audit log for every tool execution attempt.
    Avoids storing raw sensitive payloads while preserving tamper-evident hashes.
    """
    request_id: str
    task_id: str
    caller_identity: str
    tool_id: str
    tool_version: str
    arguments_hash: str
    authorization_decision: str  # "ALLOWED", "DENIED"
    policy_version: str
    dry_run: bool
    start_time: str
    end_time: str
    latency_seconds: float
    execution_status: ToolExecutionStatusEnum
    result_hash: str
    error_category: Optional[str] = None
    audit_hash: str = ""

    def compute_audit_hash(self) -> str:
        """Calculates SHA-256 digest of core audit fields for tamper-evidence."""
        payload = {
            "request_id": self.request_id,
            "task_id": self.task_id,
            "caller_identity": self.caller_identity,
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "arguments_hash": self.arguments_hash,
            "authorization_decision": self.authorization_decision,
            "policy_version": self.policy_version,
            "dry_run": self.dry_run,
            "execution_status": self.execution_status.value,
            "result_hash": self.result_hash,
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        if not self.audit_hash:
            self.audit_hash = self.compute_audit_hash()


class ToolExecutionResult(BaseModel):
    """
    Standard result returned to the caller with concise policy explanations and audit metadata.
    """
    request_id: str
    task_id: str
    tool_name: str
    status: ToolExecutionStatusEnum
    data: Optional[Dict[str, Any]] = None
    simulated: bool = False
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    latency_seconds: float = 0.0
    policy_explanation: str = Field(description="Concise human-readable authorization and policy outcome")
    audit_record: Optional[ToolExecutionAuditRecord] = None


class ToolSecurityPolicy(BaseModel):
    """
    Platform-wide tool security guardrails.
    """
    policy_version: str = "v1.0-strict"
    allow_arbitrary_python: bool = False
    allow_arbitrary_sql: bool = False
    allow_shell_commands: bool = False
    allow_filesystem_write: bool = False
    allow_network_egress: bool = False
    max_tool_calls_per_step: int = 3
    max_retrieval_iterations: int = 3
    max_total_tool_calls_per_task: int = 10
    max_total_tool_runtime_seconds: float = 15.0
    allowed_access_modes: Set[ToolAccessModeEnum] = Field(
        default_factory=lambda: {ToolAccessModeEnum.READ_ONLY, ToolAccessModeEnum.SIMULATION}
    )
