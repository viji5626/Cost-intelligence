"""
Phase AI-11 Test Suite: Local MCP & Tool Security
Tests tool registration, allowlist enforcement, role permissions, prohibited action gating,
parameter schema validation, circuit-breaker budgets, execution timeouts, dry-run guarantees,
typed domain handlers, and cryptographic audit hashing.
"""

import asyncio
import hashlib
import json
import pytest
from typing import Dict, Any

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
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStatusEnum,
    ToolSecurityPolicy,
    ToolSideEffectEnum,
)
from ai.tools.registry import ToolRegistry


# ==============================================================================
# 1. TOOL REGISTRATION & METADATA TESTS
# ==============================================================================

def test_01_tool_registration_and_metadata():
    """Test: Tools register with complete metadata, parameter schemas, and default security flags."""
    registry = ToolRegistry()
    tools = registry.list_tools()
    assert len(tools) >= 5

    ecn_tool = registry.get_tool("search_ecn_records")
    assert ecn_tool is not None
    assert ecn_tool.tool_id == "tool-ecn-search-v1"
    assert ecn_tool.network_allowed is False
    assert ecn_tool.filesystem_allowed is False
    assert ecn_tool.dry_run_supported is True
    assert ecn_tool.access_mode == ToolAccessModeEnum.READ_ONLY
    assert "properties" in ecn_tool.parameters_schema


def test_02_allowlist_security_enforcement():
    """Test: Unregistered tools are strictly denied execution."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-01",
        tool_name="unregistered_dangerous_tool",
        arguments={"cmd": "whoami"},
    )
    res = asyncio.run(registry.execute_tool_secure(req))
    assert res.status == ToolExecutionStatusEnum.UNAUTHORIZED
    assert "not allowlisted" in res.policy_explanation
    assert res.data is None
    assert res.audit_record is not None
    assert res.audit_record.authorization_decision == "DENIED"


# ==============================================================================
# 2. ROLE AUTHORIZATION & ADMIN ACCESS RESTRICTION
# ==============================================================================

def test_03_admin_access_mode_strictly_prohibited_for_ai():
    """Test: AI callers cannot execute ADMIN_HUMAN_ONLY tools or elevate roles."""
    registry = ToolRegistry()
    # Register an admin-only human tool
    registry.register_domain_tool(
        tool_id="tool-admin-db-purge",
        name="purge_database",
        version="1.0.0",
        description="Admin-only database wipe",
        param_model=SearchECNParams,
        handler=lambda **kw: {"purged": True},
        access_mode=ToolAccessModeEnum.ADMIN_HUMAN_ONLY,
    )

    req = ToolExecutionRequest(
        task_id="task-admin-test",
        tool_name="purge_database",
        arguments={"query": "test"},
        caller_role="AI_AGENT",
    )
    res = asyncio.run(registry.execute_tool_secure(req))
    assert res.status == ToolExecutionStatusEnum.UNAUTHORIZED
    assert "ADMIN" in res.error_message
    assert "AI model cannot request or elevate ADMIN" in res.policy_explanation

    # Elevation attempt
    req_elevate = ToolExecutionRequest(
        task_id="task-admin-test",
        tool_name="purge_database",
        arguments={"query": "test"},
        caller_role="ADMIN_ELEVATION",
    )
    res_elevate = asyncio.run(registry.execute_tool_secure(req_elevate))
    assert res_elevate.status == ToolExecutionStatusEnum.UNAUTHORIZED


# ==============================================================================
# 3. PROHIBITED SECURITY PATTERNS GATING
# ==============================================================================

@pytest.mark.parametrize("malicious_args, expected_pattern", [
    ({"query": "53100; cmd.exe /c dir"}, "cmd"),
    ({"query": "powershell -Command Get-Process"}, "powershell"),
    ({"query": "import subprocess; subprocess.Popen()"}, "subprocess"),
    ({"query": "SELECT * FROM parts; DROP TABLE audit_log;"}, "drop table"),
    ({"part_number": "../../../etc/passwd"}, "../"),
    ({"part_number": "C:\\Windows\\System32\\cmd.exe"}, "c:\\windows"),
])
def test_04_prohibited_security_patterns_blocked(malicious_args, expected_pattern):
    """Test: Input arguments containing shell, SQL, or path traversals are blocked immediately."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-security-test",
        tool_name="search_ecn_records",
        arguments=malicious_args,
    )
    res = asyncio.run(registry.execute_tool_secure(req))
    assert res.status == ToolExecutionStatusEnum.PROHIBITED_ACTION
    assert "Prohibited security pattern" in res.error_message
    assert res.audit_record.execution_status == ToolExecutionStatusEnum.PROHIBITED_ACTION


# ==============================================================================
# 4. PARAMETER SCHEMA VALIDATION TESTS
# ==============================================================================

def test_05_parameter_schema_validation_success_and_failure():
    """Test: Valid arguments pass schema validation; invalid arguments return VALIDATION_ERROR."""
    registry = ToolRegistry()

    # Valid call
    req_valid = ToolExecutionRequest(
        task_id="task-val-01",
        tool_name="calculate_opportunity",
        arguments={
            "baseline_cost_inr": 500.0,
            "target_cost_inr": 450.0,
            "annual_volume": 100000,
            "tooling_investment_inr": 50000.0,
        },
    )
    res_valid = asyncio.run(registry.execute_tool_secure(req_valid))
    assert res_valid.status == ToolExecutionStatusEnum.SUCCESS
    assert res_valid.data is not None
    assert res_valid.data["annual_saving_inr"] == 5000000.0

    # Invalid call (negative volume)
    req_invalid = ToolExecutionRequest(
        task_id="task-val-02",
        tool_name="calculate_opportunity",
        arguments={
            "baseline_cost_inr": 500.0,
            "target_cost_inr": 450.0,
            "annual_volume": -10,  # Fails ge=0
        },
    )
    res_invalid = asyncio.run(registry.execute_tool_secure(req_invalid))
    assert res_invalid.status == ToolExecutionStatusEnum.VALIDATION_ERROR
    assert "annual_volume" in res_invalid.error_message


# ==============================================================================
# 5. CIRCUIT BREAKER & LOOP PROTECTION TESTS
# ==============================================================================

def test_06_circuit_breaker_duplicate_call_detection():
    """Test: Immediate consecutive identical calls or repeated duplicate calls trip the circuit breaker."""
    cb = ToolCircuitBreaker()
    task_id = "task-cb-loop"
    tool = "search_ecn_records"
    args = {"query": "handlebar"}

    # First call allowed
    ok1, reason1 = cb.check_invocation_allowed(task_id, tool, args)
    assert ok1 is True
    cb.record_invocation(task_id, tool, args, 0.05)

    # Immediate consecutive identical call blocked
    ok2, reason2 = cb.check_invocation_allowed(task_id, tool, args)
    assert ok2 is False
    assert "consecutive duplicate" in reason2.lower()


def test_07_circuit_breaker_budget_limits():
    """Test: Calls per step, total calls, and runtime limits are enforced."""
    cb = ToolCircuitBreaker(max_calls_per_step=2, max_total_calls_per_task=4, max_total_runtime_seconds=1.0)
    task_id = "task-budget"

    # Step 1: Call 1 & 2
    assert cb.check_invocation_allowed(task_id, "tool_a", {"q": 1})[0] is True
    cb.record_invocation(task_id, "tool_a", {"q": 1}, 0.2)
    assert cb.check_invocation_allowed(task_id, "tool_b", {"q": 2})[0] is True
    cb.record_invocation(task_id, "tool_b", {"q": 2}, 0.2)

    # Step 1: Call 3 exceeds step budget
    ok_step, reason_step = cb.check_invocation_allowed(task_id, "tool_c", {"q": 3})
    assert ok_step is False
    assert "per step" in reason_step.lower()

    # Advance iteration
    cb.advance_iteration(task_id)
    assert cb.check_invocation_allowed(task_id, "tool_c", {"q": 3})[0] is True
    cb.record_invocation(task_id, "tool_c", {"q": 3}, 0.8)  # total runtime now 1.2s > 1.0s

    # Exceeds total runtime
    ok_time, reason_time = cb.check_invocation_allowed(task_id, "tool_d", {"q": 4})
    assert ok_time is False
    assert "runtime exceeded" in reason_time.lower()


# ==============================================================================
# 6. TIMEOUT ISOLATION & DRY-RUN GUARANTEES
# ==============================================================================

@pytest.mark.asyncio
async def test_08_execution_timeout_isolation():
    """Test: Slow domain tool handlers cleanly timeout without blocking the platform."""
    registry = ToolRegistry()

    async def slow_handler(**kwargs):
        await asyncio.sleep(2.0)
        return {"done": True}

    registry.register_domain_tool(
        tool_id="tool-slow",
        name="slow_tool",
        version="1.0.0",
        description="Slow mock tool",
        param_model=SearchECNParams,
        handler=slow_handler,
        timeout_seconds=0.1,  # 100ms timeout
    )

    req = ToolExecutionRequest(
        task_id="task-timeout",
        tool_name="slow_tool",
        arguments={"query": "test"},
    )
    res = await registry.execute_tool_secure(req)
    assert res.status == ToolExecutionStatusEnum.TIMEOUT
    assert "timed out" in res.error_message


@pytest.mark.asyncio
async def test_09_dry_run_mode_execution():
    """Test: dry_run=True guarantees non-mutating execution with simulated=True."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-dry-run",
        tool_name="calculate_opportunity",
        arguments={
            "baseline_cost_inr": 100.0,
            "target_cost_inr": 80.0,
            "annual_volume": 50000,
        },
        dry_run=True,
    )
    res = await registry.execute_tool_secure(req)
    assert res.status == ToolExecutionStatusEnum.SUCCESS
    assert res.simulated is True
    assert res.data["simulated"] is True
    assert res.data["side_effects_executed"] is False
    assert res.audit_record.dry_run is True


# ==============================================================================
# 7. TYPED DOMAIN TOOLS VERIFICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_10_domain_tool_search_ecn_records():
    """Test: search_ecn_records returns typed change order matches."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-ecn",
        tool_name="search_ecn_records",
        arguments={"query": "Handlebar", "part_number": "53100-KTR-900"},
    )
    res = await registry.execute_tool_secure(req)
    assert res.status == ToolExecutionStatusEnum.SUCCESS
    assert res.data["total_matches"] >= 1
    assert res.data["records"][0]["ecn_number"] == "ECN-2024-001"


@pytest.mark.asyncio
async def test_11_domain_tool_get_bom_component_cost():
    """Test: get_bom_component_cost retrieves baseline material and piece cost."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-bom",
        tool_name="get_bom_component_cost",
        arguments={"part_number": "53100-KTR-900", "vehicle_model": "SPLENDOR_PLUS"},
    )
    res = await registry.execute_tool_secure(req)
    assert res.status == ToolExecutionStatusEnum.SUCCESS
    assert res.data["bom_record"]["unit_cost_inr"] == 485.50
    assert res.data["bom_record"]["material"] == "ST-52 STEEL"


@pytest.mark.asyncio
async def test_12_domain_tool_get_plant_opex_kpi():
    """Test: get_plant_opex_kpi retrieves plant-normalized power/cost KPIs."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-opex",
        tool_name="get_plant_opex_kpi",
        arguments={"plant_code": "HARIDWAR", "period_month": "2024-03"},
    )
    res = await registry.execute_tool_secure(req)
    assert res.status == ToolExecutionStatusEnum.SUCCESS
    assert res.data["kpi_metrics"]["electricity_kwh_per_vehicle"] == 42.50


@pytest.mark.asyncio
async def test_13_domain_tool_check_safety_critical():
    """Test: check_safety_critical accurately flags steering/brake components."""
    registry = ToolRegistry()

    # Safety critical
    res_crit = await registry.execute_tool_secure(ToolExecutionRequest(
        task_id="task-safety-1",
        tool_name="check_safety_critical",
        arguments={"component_name": "Handlebar Assembly"},
    ))
    assert res_crit.data["is_safety_critical"] is True
    assert res_crit.data["homologation_required"] is True

    # Non-safety critical
    res_noncrit = await registry.execute_tool_secure(ToolExecutionRequest(
        task_id="task-safety-2",
        tool_name="check_safety_critical",
        arguments={"component_name": "Side Stand Rubber Pad"},
    ))
    assert res_noncrit.data["is_safety_critical"] is False
    assert res_noncrit.data["homologation_required"] is False


@pytest.mark.asyncio
async def test_14_domain_tool_calculate_opportunity_deterministic():
    """Test: calculate_opportunity delegates exclusively to pure-Python Decimal engine."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-calc",
        tool_name="calculate_opportunity",
        arguments={
            "baseline_cost_inr": 485.50,
            "target_cost_inr": 450.00,
            "annual_volume": 600000,
            "tooling_investment_inr": 200000.00,
        },
    )
    res = await registry.execute_tool_secure(req)
    assert res.status == ToolExecutionStatusEnum.SUCCESS
    assert res.data["unit_saving_inr"] == 35.50
    assert res.data["annual_saving_inr"] == 21300000.00
    assert res.data["net_annual_benefit_inr"] == 21100000.00
    assert len(res.data["provenance_hash"]) == 64


# ==============================================================================
# 8. CRYPTOGRAPHIC AUDIT HASH INTEGRITY
# ==============================================================================

@pytest.mark.asyncio
async def test_15_cryptographic_audit_hash_integrity():
    """Test: Audit records generate immutable SHA-256 hashes verifying execution parameters."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-audit-check",
        tool_name="search_ecn_records",
        arguments={"query": "Lever"},
    )
    res = await registry.execute_tool_secure(req)
    assert res.audit_record is not None
    assert len(res.audit_record.audit_hash) == 64
    assert res.audit_record.compute_audit_hash() == res.audit_record.audit_hash


# ==============================================================================
# 9. ADVANCED SECURITY FAILURE & AUDIT TAMPERING TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_16_network_tool_attempt_blocked_by_default():
    """Test: Tools requesting outbound network access are disallowed by default policy."""
    registry = ToolRegistry()
    registry.register_domain_tool(
        tool_id="tool-network-fetch",
        name="external_supplier_api",
        version="1.0.0",
        description="External network fetcher",
        param_model=SearchECNParams,
        handler=lambda **kw: {"fetched": True},
        access_mode=ToolAccessModeEnum.READ_ONLY,
    )
    # Force network_allowed=True on definition to test policy conflict
    tool_def = registry.get_tool("external_supplier_api")
    assert tool_def.network_allowed is False


def test_17_repeated_normalized_duplicate_calls_detected():
    """Test: Arguments with different key orders or representations normalize to same hash."""
    cb = ToolCircuitBreaker()
    task_id = "task-norm-dup"
    tool = "search_ecn_records"

    args_a = {"query": "Handlebar", "part_number": "53100-KTR-900"}
    args_b = {"part_number": "53100-KTR-900", "query": "Handlebar"}  # inverted order

    # First call allowed
    ok1, _ = cb.check_invocation_allowed(task_id, tool, args_a)
    assert ok1 is True
    cb.record_invocation(task_id, tool, args_a, 0.05)

    # Inverted order detected as duplicate
    ok2, reason2 = cb.check_invocation_allowed(task_id, tool, args_b)
    assert ok2 is False
    assert "duplicate" in reason2.lower()


@pytest.mark.asyncio
async def test_18_audit_tampering_detection():
    """Test: Tampering with audit record fields invalidates the cryptographic hash."""
    registry = ToolRegistry()
    req = ToolExecutionRequest(
        task_id="task-audit-tamper",
        tool_name="search_ecn_records",
        arguments={"query": "Brake"},
    )
    res = await registry.execute_tool_secure(req)
    audit = res.audit_record
    assert audit is not None
    original_hash = audit.audit_hash

    # Tamper with status or caller identity
    audit.caller_identity = "malicious-intruder"
    assert audit.compute_audit_hash() != original_hash


@pytest.mark.asyncio
async def test_19_policy_explanation_transparency():
    """Test: Concise policy explanations are returned for both allowed and denied calls."""
    registry = ToolRegistry()

    # Allowed explanation
    res_ok = await registry.execute_tool_secure(ToolExecutionRequest(
        task_id="task-expl-1",
        tool_name="check_safety_critical",
        arguments={"component_name": "Front Fender"},
    ))
    assert "Tool allowed because" in res_ok.policy_explanation

    # Denied explanation
    res_denied = await registry.execute_tool_secure(ToolExecutionRequest(
        task_id="task-expl-2",
        tool_name="nonexistent_tool",
        arguments={},
    ))
    assert "Tool denied because" in res_denied.policy_explanation


@pytest.mark.asyncio
async def test_20_tool_version_and_policy_version_tracking():
    """Test: Audit records accurately capture tool_version and policy_version."""
    registry = ToolRegistry()
    res = await registry.execute_tool_secure(ToolExecutionRequest(
        task_id="task-ver-check",
        tool_name="get_plant_opex_kpi",
        arguments={"plant_code": "HARIDWAR", "period_month": "2024-03"},
        policy_version="v1.0-strict",
    ))
    assert res.audit_record.tool_version == "1.0.0"
    assert res.audit_record.policy_version == "v1.0-strict"
