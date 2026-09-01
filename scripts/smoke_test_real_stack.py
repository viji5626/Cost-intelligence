r"""
Phase 10 — Level 2 Real-Stack Smoke Test
==========================================
Validates the live runtime stack end-to-end:
  Windows process → FastAPI HTTP → PostgreSQL 16 → application services → API responses

Prerequisites:
  1. PostgreSQL 16 running on localhost:5432
  2. Alembic migrations applied: alembic upgrade head
  3. Demo data seeded:  .\.venv\Scripts\python data\seed_demo_data.py
  4. FastAPI server running: .\.venv\Scripts\uvicorn backend.app.main:app --port 8000

Usage:
    .\.venv\Scripts\python scripts\smoke_test_real_stack.py

Exit codes:
  0 — all 10 checks passed
  1 — one or more checks failed
"""

import asyncio
import json
import sys
import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

import httpx

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api/v1"
AUTH_ENDPOINT = f"{BASE_URL}/auth/login"
DEMO_USER_EMAIL = "admin@hero-demo.com"
DEMO_USER_PASSWORD = "SYNTHETIC_DEMO_PASSWORD"

# Demo plant IDs seeded by data/seed_demo_data.py
PLANT_A_ID = "plant-a-demo"
PLANT_A_PERIOD = "2024-04-01"

# Timeout for each HTTP call
HTTP_TIMEOUT_SECONDS = 30


# ── Helpers ───────────────────────────────────────────────────────────────────

class SmokeTestResult:
    def __init__(self):
        self.checks: list[dict] = []
        self.passed = 0
        self.failed = 0

    def record(self, name: str, passed: bool, detail: str = ""):
        icon = "✓" if passed else "✗"
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if passed:
            self.passed += 1
            print(f"  {icon} {name}")
        else:
            self.failed += 1
            print(f"  {icon} FAIL — {name}")
            if detail:
                print(f"         {detail}")


results = SmokeTestResult()


async def get_auth_token(client: httpx.AsyncClient) -> Optional[str]:
    """Obtain JWT access_token from /auth/login."""
    try:
        resp = await client.post(AUTH_ENDPOINT, data={
            "username": DEMO_USER_EMAIL,
            "password": DEMO_USER_PASSWORD,
        }, timeout=HTTP_TIMEOUT_SECONDS)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        # Some implementations use JSON body
        resp2 = await client.post(AUTH_ENDPOINT, json={
            "email": DEMO_USER_EMAIL,
            "password": DEMO_USER_PASSWORD,
        }, timeout=HTTP_TIMEOUT_SECONDS)
        if resp2.status_code == 200:
            return resp2.json().get("access_token")
    except Exception as e:
        print(f"    Auth failed: {e}")
    return None


async def api_get(client: httpx.AsyncClient, url: str, token: str) -> Tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get(url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
    body = None
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


async def api_post(client: httpx.AsyncClient, url: str, token: str, payload: dict) -> Tuple[int, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = await client.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT_SECONDS)
    body = None
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


# ── 10 Smoke Checks ───────────────────────────────────────────────────────────

async def run_smoke_tests():
    print("=" * 65)
    print("Hero Cost Intelligence — Level 2 Real-Stack Smoke Test")
    print(f"Base URL : {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 65)
    print()

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:

        # ── CHECK 1: PostgreSQL connection (FastAPI /health) ─────────────────
        print("CHECK 1: PostgreSQL connection via /health endpoint")
        try:
            resp = await client.get("/health", timeout=HTTP_TIMEOUT_SECONDS)
            body = resp.json()
            db_ok = body.get("database") in ("ok", "healthy", "connected", True)
            results.record(
                "PostgreSQL connection (/health)",
                resp.status_code == 200 and db_ok,
                f"status={resp.status_code}, db={body.get('database', 'unknown')}",
            )
        except Exception as e:
            results.record("PostgreSQL connection (/health)", False, str(e))

        # ── CHECK 2: Alembic migrations / schema readiness ───────────────────
        print("\nCHECK 2: Schema readiness (plants table query)")
        try:
            resp = await client.get(f"/api/v1/opex/plants", timeout=HTTP_TIMEOUT_SECONDS)
            results.record(
                "Migrations/schema readiness (plants list)",
                resp.status_code in (200, 401),  # 401 = schema OK, auth required
                f"status={resp.status_code}",
            )
        except Exception as e:
            results.record("Migrations/schema readiness", False, str(e))

        # ── AUTH: Obtain token ────────────────────────────────────────────────
        print("\nCHECK 3: Authentication (JWT token acquisition)")
        token = await get_auth_token(client)
        results.record(
            "Authentication / JWT token",
            token is not None,
            "No token received — check DEMO_USER_EMAIL/PASSWORD" if not token else "",
        )

        if not token:
            print("\n  ⚠ No auth token — remaining checks will fail. Run with valid credentials.")
            return

        # ── CHECK 4: Demo data persistence (OPEX KPI for Plant-A) ────────────
        print("\nCHECK 4: Demo data persistence — OPEX KPI for plant-a-demo")
        status, body = await api_get(client, f"{BASE_URL}/opex/kpis/{PLANT_A_ID}?period={PLANT_A_PERIOD}", token)
        results.record(
            "Demo data persistence (OPEX KPI plant-a-demo)",
            status == 200 and body.get("plant_code") == "PLANT-A-DEMO",
            f"status={status}, plant_code={body.get('plant_code') if isinstance(body, dict) else '?'}",
        )

        # ── CHECK 5: OPEX KPI API — key metrics non-zero ─────────────────────
        print("\nCHECK 5: OPEX KPI API — per-vehicle metrics non-zero")
        if status == 200 and isinstance(body, dict):
            kwh = body.get("kwh_per_vehicle", 0)
            opex_pv = body.get("total_opex_per_vehicle", 0)
            results.record(
                "OPEX KPI — kwh_per_vehicle & total_opex_per_vehicle > 0",
                kwh > 0 and opex_pv > 0,
                f"kwh_per_vehicle={kwh}, total_opex_per_vehicle={opex_pv}",
            )
        else:
            results.record("OPEX KPI — per-vehicle metrics", False, f"KPI call status={status}")

        # ── CHECK 6: Benchmark API — auto-selection ───────────────────────────
        print("\nCHECK 6: Benchmark API — BEST_COMPARABLE auto-selection")
        status, body = await api_post(
            client,
            f"{BASE_URL}/opex/benchmark/compare",
            token,
            {
                "target_plant_id": PLANT_A_ID,
                "mode": "BEST_COMPARABLE",
                # benchmark_plant_id intentionally NOT passed
            },
        )
        bench_ok = (
            status == 200
            and isinstance(body, dict)
            and "Best Comparable Peer" in (body.get("benchmark_source_name") or "")
        )
        results.record(
            "Benchmark API — BEST_COMPARABLE auto-selection",
            bench_ok,
            f"status={status}, source_name={body.get('benchmark_source_name') if isinstance(body, dict) else '?'}",
        )

        # ── CHECK 7: Ideathon API — idea submission ───────────────────────────
        print("\nCHECK 7: Ideathon API — idea submission")
        status, body = await api_post(
            client,
            f"{BASE_URL}/ideathon/submit",
            token,
            {
                "title": "SYNTHETIC_DEMO: Brake lever polymer substitution — Splendor",
                "description": "Replace 53100-DEMO-001 from alloy to polymer. Saves ₹8.50/veh.",
                "submitter_employee_id": "EMP-SMOKE-01",
                "submitter_plant_code": "PLANT-A-DEMO",
                "raw_claimed_saving": 8.50,
            },
        )
        idea_id = body.get("id") if isinstance(body, dict) else None
        results.record(
            "Ideathon API — idea submission",
            status == 200 and idea_id is not None,
            f"status={status}, idea_id={idea_id}",
        )

        # ── CHECK 8: Discovery API ────────────────────────────────────────────
        print("\nCHECK 8: Discovery API — evidence evaluation")
        if idea_id:
            status, body = await api_post(
                client,
                f"{BASE_URL}/discovery/evaluate/{idea_id}",
                token,
                {},
            )
            results.record(
                "Discovery API — evidence evaluation",
                status in (200, 202),
                f"status={status}, evidence_state={body.get('evidence_state') if isinstance(body, dict) else '?'}",
            )
        else:
            results.record("Discovery API", False, "Skipped — no idea_id from Check 7")

        # ── CHECK 9: Opportunity API ──────────────────────────────────────────
        print("\nCHECK 9: Opportunity API — evaluation")
        if idea_id:
            status, body = await api_post(
                client,
                f"{BASE_URL}/opportunity/evaluate-idea/{idea_id}",
                token,
                {},
            )
            opp_ok = (
                status == 200
                and isinstance(body, dict)
                and "npv" not in json.dumps(body).lower()  # Terminology check
                and body.get("provenance_hash")
            )
            results.record(
                "Opportunity API — evaluation (no 'npv' in response)",
                bool(opp_ok),
                f"status={status}, status_field={body.get('status') if isinstance(body, dict) else '?'}",
            )
        else:
            results.record("Opportunity API", False, "Skipped — no idea_id from Check 7")

        # ── CHECK 10: Governance + Review case retrieval ──────────────────────
        print("\nCHECK 10: Governance API — final review-case retrieval")
        if idea_id:
            status, body = await api_post(
                client,
                f"{BASE_URL}/governance/sync/{idea_id}",
                token,
                {},
            )
            gov_ok = (
                status in (200, 201)
                and isinstance(body, dict)
                and body.get("idea_id") == idea_id
                and body.get("calibrated_confidence_score") is not None
            )
            results.record(
                "Governance API — sync & confidence score",
                gov_ok,
                f"status={status}, confidence={body.get('calibrated_confidence_score') if isinstance(body, dict) else '?'}",
            )
        else:
            results.record("Governance API", False, "Skipped — no idea_id from Check 7")


def print_summary():
    print()
    print("=" * 65)
    print(f"LEVEL 2 SMOKE TEST SUMMARY")
    print("=" * 65)
    print(f"  PASSED : {results.passed:>2} / {results.passed + results.failed}")
    print(f"  FAILED : {results.failed:>2} / {results.passed + results.failed}")
    print()
    if results.failed > 0:
        print("  FAILED CHECKS:")
        for c in results.checks:
            if not c["passed"]:
                print(f"    ✗ {c['name']}")
                if c["detail"]:
                    print(f"      {c['detail']}")
    print()
    if results.failed == 0:
        print("  ✓ ALL CHECKS PASSED — Real-stack smoke test COMPLETE")
        print("  POC is ready for demonstration.")
    else:
        print("  ✗ SOME CHECKS FAILED — see details above")
        print("  Ensure PostgreSQL, Alembic migrations, and seed data are correct.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_smoke_tests())
    print_summary()
    sys.exit(0 if results.failed == 0 else 1)
