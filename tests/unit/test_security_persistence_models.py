"""
Unit Tests for Security & Persistence Foundation Models (Phase P1)
Verifies User, UserSession, SecurityPolicy, AuditLog, UserActivityEvent, and SystemRuntimeConfig.
"""

from datetime import datetime, timezone, timedelta
from database.models.auth import User
from database.models.session import UserSession
from database.models.security_policy import SecurityPolicy
from database.models.audit import AuditLog
from database.models.activity import UserActivityEvent
from database.models.runtime_config import SystemRuntimeConfig


def test_user_model_instantiation_and_defaults():
    user = User(
        username="admin_hero",
        email="admin@hero.internal",
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        display_name="Hero Chief Administrator",
        role="ADMINISTRATOR",
    )
    assert user.username == "admin_hero"
    assert user.email == "admin@hero.internal"
    assert user.display_name == "Hero Chief Administrator"
    assert user.role == "ADMINISTRATOR"
    assert user.is_active is True
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert user.plant_scope == ["ALL"]
    assert user.department == "ENGINEERING"
    assert isinstance(user.password_changed_at, datetime)


def test_user_session_model_instantiation():
    now = datetime.now(timezone.utc)
    session = UserSession(
        user_id="user-uuid-1234",
        session_token="token-abc-xyz-5678",
        client_ip="192.168.1.50",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        is_active=True,
        expires_at=now + timedelta(hours=8),
    )
    assert session.user_id == "user-uuid-1234"
    assert session.session_token == "token-abc-xyz-5678"
    assert session.client_ip == "192.168.1.50"
    assert session.is_active is True
    assert session.expires_at > now


def test_security_policy_model_instantiation():
    policy = SecurityPolicy(
        min_password_length=10,
        require_uppercase=True,
        require_lowercase=True,
        require_digit=True,
        require_special_char=True,
        max_failed_attempts=5,
        lockout_duration_minutes=15,
        session_inactivity_timeout_minutes=480,
    )
    assert policy.min_password_length == 10
    assert policy.max_failed_attempts == 5
    assert policy.lockout_duration_minutes == 15
    assert policy.session_inactivity_timeout_minutes == 480


def test_audit_log_hash_chain_fields():
    audit_entry = AuditLog(
        sequence_number=1,
        username="admin_hero",
        role="ADMINISTRATOR",
        action="SYSTEM_BOOTSTRAPPED",
        entity_type="SYSTEM",
        entity_id="ROOT",
        status="SUCCESS",
        previous_event_hash="0" * 64,
        event_hash="sha256:abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yzab5678cdef9012",
        payload_json={"message": "System bootstrapped successfully"},
    )
    assert audit_entry.sequence_number == 1
    assert audit_entry.action == "SYSTEM_BOOTSTRAPPED"
    assert audit_entry.previous_event_hash == "0" * 64
    assert audit_entry.event_hash.startswith("sha256:")
    assert audit_entry.payload_json["message"] == "System bootstrapped successfully"


def test_user_activity_event_instantiation():
    activity = UserActivityEvent(
        session_id="session-uuid-9999",
        user_id="user-uuid-1234",
        username="cost_eng_1",
        activity_type="PLANT_SELECTED",
        page="OPEX_BENCHMARKING",
        plant_id="HARIDWAR",
        entity_type="PLANT",
        entity_id="HARIDWAR",
        details_json={"selected_tab": "SPECIFIC_POWER"},
    )
    assert activity.session_id == "session-uuid-9999"
    assert activity.activity_type == "PLANT_SELECTED"
    assert activity.plant_id == "HARIDWAR"
    assert activity.details_json["selected_tab"] == "SPECIFIC_POWER"


def test_system_runtime_config_instantiation():
    runtime = SystemRuntimeConfig(
        is_default=True,
        provider="llama_cpp",
        model_id="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        model_hash="sha256:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        runtime_profile="BALANCED",
        context_length=8192,
        gpu_layers=35,
        is_active=True,
    )
    assert runtime.is_default is True
    assert runtime.provider == "llama_cpp"
    assert runtime.model_id == "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    assert runtime.context_length == 8192
    assert runtime.gpu_layers == 35
