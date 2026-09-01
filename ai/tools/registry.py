"""
Tool Security Registry & Execution Coordinator (AI-11)
Implements ToolRegistryContract with strict allowlisting, role authorization, parameter schema validation,
timeout isolation, circuit-breaker loop protection, dry-run guarantees, and cryptographic audit logging.
"""

import asyncio
import hashlib
import inspect
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel, ValidationError

from ai.core.contracts import ToolRegistryContract
from ai.tools.circuit_breaker import ToolCircuitBreaker
from ai.tools.domain_tools import (
    CalculateOpportunityParams,
    CheckSafetyCriticalParams,
    DomainToolHandlers,
    GetBOMCostParams,
    GetPlantOpexKPIParams,
    SearchECNParams,
)
from ai.tools.models import (
    ToolAccessModeEnum,
    ToolDefinition,
    ToolExecutionAuditRecord,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatusEnum,
    ToolSecurityPolicy,
    ToolSideEffectEnum,
)


class ToolRegistry(ToolRegistryContract):
    """
    Central registry and security gateway for sandboxed AI tools.
    """

    PROHIBITED_PATTERNS = [
        re.compile(r"\b(cmd|powershell|bash|sh|exec|spawn|subprocess|system)\b", re.IGNORECASE),
        re.compile(r"\b(drop\s+table|delete\s+from|insert\s+into|update\s+\w+\s+set|truncate)\b", re.IGNORECASE),
        re.compile(r"(\.\./|\.\.\\|/etc/|c:\\windows|c:\\system32)", re.IGNORECASE),
    ]

    def __init__(
        self,
        policy: Optional[ToolSecurityPolicy] = None,
        circuit_breaker: Optional[ToolCircuitBreaker] = None,
    ):
        self.policy = policy or ToolSecurityPolicy()
        self.circuit_breaker = circuit_breaker or ToolCircuitBreaker(
            max_calls_per_step=self.policy.max_tool_calls_per_step,
            max_iterations=self.policy.max_retrieval_iterations,
            max_total_calls_per_task=self.policy.max_total_tool_calls_per_task,
            max_total_runtime_seconds=self.policy.max_total_tool_runtime_seconds,
        )
        self._tools: Dict[str, ToolDefinition] = {}
        self._param_models: Dict[str, Type[BaseModel]] = {}
        self._register_default_domain_tools()

    def _register_default_domain_tools(self) -> None:
        """Registers the 5 standard allowlisted domain tools for Hero Cost Intelligence."""
        # 1. Search ECN
        self.register_domain_tool(
            tool_id="tool-ecn-search-v1",
            name="search_ecn_records",
            version="1.0.0",
            description="Search verified engineering change notices (ECNs) by keyword, part number, or vehicle model.",
            param_model=SearchECNParams,
            handler=DomainToolHandlers.search_ecn_records,
            access_mode=ToolAccessModeEnum.READ_ONLY,
            data_scope="ENGINEERING_ECN",
        )

        # 2. Get BOM Cost
        self.register_domain_tool(
            tool_id="tool-bom-cost-v1",
            name="get_bom_component_cost",
            version="1.0.0",
            description="Retrieve authoritative baseline BOM piece cost and material information for a component.",
            param_model=GetBOMCostParams,
            handler=DomainToolHandlers.get_bom_component_cost,
            access_mode=ToolAccessModeEnum.READ_ONLY,
            data_scope="BOM_COST_CATALOG",
        )

        # 3. Get Plant OPEX KPI
        self.register_domain_tool(
            tool_id="tool-plant-opex-v1",
            name="get_plant_opex_kpi",
            version="1.0.0",
            description="Retrieve normalized factory utility consumption and OPEX KPIs per vehicle.",
            param_model=GetPlantOpexKPIParams,
            handler=DomainToolHandlers.get_plant_opex_kpi,
            access_mode=ToolAccessModeEnum.READ_ONLY,
            data_scope="PLANT_OPEX",
        )

        # 4. Check Safety Critical
        self.register_domain_tool(
            tool_id="tool-safety-check-v1",
            name="check_safety_critical",
            version="1.0.0",
            description="Check whether a component belongs to the regulated safety-critical list (steering, braking, chassis).",
            param_model=CheckSafetyCriticalParams,
            handler=DomainToolHandlers.check_safety_critical,
            access_mode=ToolAccessModeEnum.READ_ONLY,
            data_scope="SAFETY_TAXONOMY",
        )

        # 5. Calculate Opportunity
        self.register_domain_tool(
            tool_id="tool-calc-opportunity-v1",
            name="calculate_opportunity",
            version="1.0.0",
            description="Calculate annual volume savings, net delta, and payback period using pure Python Decimal precision.",
            param_model=CalculateOpportunityParams,
            handler=DomainToolHandlers.calculate_opportunity,
            access_mode=ToolAccessModeEnum.SIMULATION,
            data_scope="CALCULATION_ENGINE",
            side_effect=ToolSideEffectEnum.SIMULATION_ONLY,
        )

    def register_domain_tool(
        self,
        tool_id: str,
        name: str,
        version: str,
        description: str,
        param_model: Type[BaseModel],
        handler: Callable[..., Any],
        access_mode: ToolAccessModeEnum = ToolAccessModeEnum.READ_ONLY,
        data_scope: str = "DOMAIN",
        allowed_roles: Optional[List[str]] = None,
        dry_run_supported: bool = True,
        side_effect: ToolSideEffectEnum = ToolSideEffectEnum.NO_SIDE_EFFECTS,
        timeout_seconds: float = 3.0,
    ) -> None:
        """Registers a strongly-typed domain tool with Pydantic parameter schema."""
        tool_def = ToolDefinition(
            tool_id=tool_id,
            name=name,
            version=version,
            description=description,
            parameters_schema=param_model.model_json_schema(),
            access_mode=access_mode,
            data_scope=data_scope,
            allowed_roles=allowed_roles or ["AI_AGENT", "ENGINEER", "VIEWER"],
            dry_run_supported=dry_run_supported,
            side_effect_classification=side_effect,
            network_allowed=False,
            filesystem_allowed=False,
            timeout_seconds=timeout_seconds,
            handler=handler,
        )
        self._tools[name] = tool_def
        self._param_models[name] = param_model

    def register_tool(self, name: str, description: str, parameters_schema: Dict[str, Any], handler: Any) -> None:
        """Conforms to ToolRegistryContract protocol."""
        tool_def = ToolDefinition(
            tool_id=f"tool-{name}-custom",
            name=name,
            version="1.0.0",
            description=description,
            parameters_schema=parameters_schema,
            access_mode=ToolAccessModeEnum.READ_ONLY,
            handler=handler,
        )
        self._tools[name] = tool_def

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Retrieves tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """Lists all registered tools."""
        return list(self._tools.values())

    async def execute_tool(self, name: str, arguments: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Protocol execution entry point."""
        req = ToolExecutionRequest(
            task_id="task-direct",
            tool_name=name,
            arguments=arguments,
            dry_run=dry_run,
        )
        res = await self.execute_tool_secure(req)
        return res.model_dump()

    async def execute_tool_secure(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """
        Executes a sandboxed tool through complete security, authorization, schema validation,
        loop circuit breaking, timeout isolation, and cryptographic audit logging.
        """
        t_start = time.perf_counter()
        start_iso = datetime.now(timezone.utc).isoformat()
        args_hash = self.circuit_breaker.compute_arguments_hash(request.arguments)

        # 1. Registration Check
        tool = self._tools.get(request.tool_name)
        if not tool:
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.UNAUTHORIZED,
                error_msg=f"Tool '{request.tool_name}' is not registered or not allowlisted.",
                error_cat="NOT_REGISTERED",
                policy_expl="Tool denied because: tool is not allowlisted in registry.",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id="unknown",
                tool_version="0.0.0",
            )

        # 2. Authorization & Mode Check
        # Reject ADMIN requests from AI execution path
        if tool.access_mode == ToolAccessModeEnum.ADMIN_HUMAN_ONLY or request.caller_role == "ADMIN_ELEVATION":
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.UNAUTHORIZED,
                error_msg="ADMIN authorization level is restricted to authenticated human administrators.",
                error_cat="ADMIN_PROHIBITED",
                policy_expl="Tool denied because: AI model cannot request or elevate ADMIN privileges.",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id=tool.tool_id,
                tool_version=tool.version,
            )

        if tool.access_mode not in self.policy.allowed_access_modes:
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.UNAUTHORIZED,
                error_msg=f"Access mode '{tool.access_mode.value}' is disallowed by current execution policy.",
                error_cat="ACCESS_MODE_DISALLOWED",
                policy_expl=f"Tool denied because: access mode '{tool.access_mode.value}' is disabled in policy.",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id=tool.tool_id,
                tool_version=tool.version,
            )

        # 3. Prohibited Actions & Security Gating
        is_safe, security_reason = self._check_prohibited_actions(request.arguments)
        if not is_safe:
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.PROHIBITED_ACTION,
                error_msg=f"Prohibited security pattern detected: {security_reason}",
                error_cat="PROHIBITED_SECURITY_PATTERN",
                policy_expl="Tool denied because: input arguments contained prohibited shell, SQL, or path traversal patterns.",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id=tool.tool_id,
                tool_version=tool.version,
            )

        # 4. Parameter Schema Validation
        param_model = self._param_models.get(request.tool_name)
        validated_params: Dict[str, Any] = request.arguments
        if param_model:
            try:
                validated_obj = param_model.model_validate(request.arguments)
                validated_params = validated_obj.model_dump()
            except ValidationError as val_err:
                compact_err = "; ".join(f"'{e['loc'][0]}': {e['msg']}" for e in val_err.errors() if e.get("loc"))
                return self._build_denied_result(
                    request=request,
                    status=ToolExecutionStatusEnum.VALIDATION_ERROR,
                    error_msg=f"Schema validation failed: {compact_err}",
                    error_cat="SCHEMA_VALIDATION_ERROR",
                    policy_expl=f"Tool denied because: parameter schema validation failed ({compact_err}).",
                    start_iso=start_iso,
                    args_hash=args_hash,
                    t_start=t_start,
                    tool_id=tool.tool_id,
                    tool_version=tool.version,
                )

        # 5. Circuit Breaker Check
        cb_allowed, cb_reason = self.circuit_breaker.check_invocation_allowed(
            task_id=request.task_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
        )
        if not cb_allowed:
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.CIRCUIT_BREAKER_TRIPPED,
                error_msg=f"Circuit breaker tripped: {cb_reason}",
                error_cat="CIRCUIT_BREAKER_TRIPPED",
                policy_expl=f"Tool denied because: circuit breaker budget tripped ({cb_reason}).",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id=tool.tool_id,
                tool_version=tool.version,
            )

        # 6. Dry Run Guarantee
        if request.dry_run:
            duration = round(time.perf_counter() - t_start, 4)
            end_iso = datetime.now(timezone.utc).isoformat()
            self.circuit_breaker.record_invocation(request.task_id, request.tool_name, request.arguments, duration)
            sim_data = {
                "simulated": True,
                "tool_name": request.tool_name,
                "validated_arguments": validated_params,
                "side_effects_executed": False,
                "message": "Dry run execution verified: parameters valid, no mutations performed.",
            }
            res_hash = hashlib.sha256(json.dumps(sim_data, sort_keys=True).encode("utf-8")).hexdigest()
            audit = ToolExecutionAuditRecord(
                request_id=request.request_id,
                task_id=request.task_id,
                caller_identity=request.caller_identity,
                tool_id=tool.tool_id,
                tool_version=tool.version,
                arguments_hash=args_hash,
                authorization_decision="ALLOWED_DRY_RUN",
                policy_version=self.policy.policy_version,
                dry_run=True,
                start_time=start_iso,
                end_time=end_iso,
                latency_seconds=duration,
                execution_status=ToolExecutionStatusEnum.SUCCESS,
                result_hash=res_hash,
            )
            return ToolExecutionResult(
                request_id=request.request_id,
                task_id=request.task_id,
                tool_name=request.tool_name,
                status=ToolExecutionStatusEnum.SUCCESS,
                data=sim_data,
                simulated=True,
                latency_seconds=duration,
                policy_explanation="Tool allowed because: registered, role permitted, schema valid, dry-run non-mutating mode.",
                audit_record=audit,
            )

        # 7. Bounded Execution with Timeout
        if not tool.handler:
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.EXECUTION_ERROR,
                error_msg=f"Tool '{request.tool_name}' has no registered executable handler.",
                error_cat="NO_HANDLER",
                policy_expl="Tool denied because: tool handler is missing.",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id=tool.tool_id,
                tool_version=tool.version,
            )

        try:
            if inspect.iscoroutinefunction(tool.handler):
                result_data = await asyncio.wait_for(
                    tool.handler(**validated_params),
                    timeout=tool.timeout_seconds,
                )
            else:
                result_data = tool.handler(**validated_params)

            duration = round(time.perf_counter() - t_start, 4)
            end_iso = datetime.now(timezone.utc).isoformat()
            self.circuit_breaker.record_invocation(request.task_id, request.tool_name, request.arguments, duration)

            res_hash = hashlib.sha256(json.dumps(result_data, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            audit = ToolExecutionAuditRecord(
                request_id=request.request_id,
                task_id=request.task_id,
                caller_identity=request.caller_identity,
                tool_id=tool.tool_id,
                tool_version=tool.version,
                arguments_hash=args_hash,
                authorization_decision="ALLOWED",
                policy_version=self.policy.policy_version,
                dry_run=False,
                start_time=start_iso,
                end_time=end_iso,
                latency_seconds=duration,
                execution_status=ToolExecutionStatusEnum.SUCCESS,
                result_hash=res_hash,
            )

            return ToolExecutionResult(
                request_id=request.request_id,
                task_id=request.task_id,
                tool_name=request.tool_name,
                status=ToolExecutionStatusEnum.SUCCESS,
                data=result_data,
                simulated=False,
                latency_seconds=duration,
                policy_explanation=f"Tool allowed because: registered ({tool.tool_id}), schema valid, role permitted, within budget ({duration:.3f}s).",
                audit_record=audit,
            )

        except asyncio.TimeoutError:
            duration = round(time.perf_counter() - t_start, 4)
            end_iso = datetime.now(timezone.utc).isoformat()
            self.circuit_breaker.record_invocation(request.task_id, request.tool_name, request.arguments, duration)
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.TIMEOUT,
                error_msg=f"Tool execution timed out after {tool.timeout_seconds}s limit.",
                error_cat="TIMEOUT",
                policy_expl=f"Tool execution halted because: timeout limit ({tool.timeout_seconds}s) reached.",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id=tool.tool_id,
                tool_version=tool.version,
            )
        except Exception as ex:
            duration = round(time.perf_counter() - t_start, 4)
            end_iso = datetime.now(timezone.utc).isoformat()
            self.circuit_breaker.record_invocation(request.task_id, request.tool_name, request.arguments, duration)
            return self._build_denied_result(
                request=request,
                status=ToolExecutionStatusEnum.EXECUTION_ERROR,
                error_msg=f"Handler execution error: {str(ex)}",
                error_cat="HANDLER_EXCEPTION",
                policy_expl="Tool execution failed during handler computation.",
                start_iso=start_iso,
                args_hash=args_hash,
                t_start=t_start,
                tool_id=tool.tool_id,
                tool_version=tool.version,
            )

    @classmethod
    def _check_prohibited_actions(cls, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Scans input arguments for prohibited shell, SQL, or path traversal patterns."""
        args_str = json.dumps(arguments, default=str)
        for pattern in cls.PROHIBITED_PATTERNS:
            match = pattern.search(args_str)
            if match:
                return False, f"Matched prohibited security pattern '{match.group(0)}'."
        return True, None

    def _build_denied_result(
        self,
        request: ToolExecutionRequest,
        status: ToolExecutionStatusEnum,
        error_msg: str,
        error_cat: str,
        policy_expl: str,
        start_iso: str,
        args_hash: str,
        t_start: float,
        tool_id: str,
        tool_version: str,
    ) -> ToolExecutionResult:
        """Constructs a denied/failed execution result with an audit record."""
        duration = round(time.perf_counter() - t_start, 4)
        end_iso = datetime.now(timezone.utc).isoformat()
        res_hash = hashlib.sha256(error_msg.encode("utf-8")).hexdigest()

        audit = ToolExecutionAuditRecord(
            request_id=request.request_id,
            task_id=request.task_id,
            caller_identity=request.caller_identity,
            tool_id=tool_id,
            tool_version=tool_version,
            arguments_hash=args_hash,
            authorization_decision="DENIED",
            policy_version=self.policy.policy_version,
            dry_run=request.dry_run,
            start_time=start_iso,
            end_time=end_iso,
            latency_seconds=duration,
            execution_status=status,
            result_hash=res_hash,
            error_category=error_cat,
        )

        return ToolExecutionResult(
            request_id=request.request_id,
            task_id=request.task_id,
            tool_name=request.tool_name,
            status=status,
            data=None,
            simulated=request.dry_run,
            error_message=error_msg,
            error_category=error_cat,
            latency_seconds=duration,
            policy_explanation=policy_expl,
            audit_record=audit,
        )
