# ============================================================
# Hero Cost Intelligence — Phase 10 Dev Startup Script
# ============================================================
# Starts the complete local development stack on Windows.
#
# Prerequisites:
#   • PostgreSQL 16 running on localhost:5432
#   • .venv created: uv venv .venv && .venv\Scripts\activate
#   • Dependencies installed: uv pip sync requirements.txt
#   • .env file configured with DATABASE_URL etc.
#
# Usage: .\scripts\start_dev.ps1
# ============================================================

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $Root

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Hero Cost Intelligence — Starting Dev Stack" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Activate venv ──────────────────────────────────────────────────────────
if (-not (Test-Path ".venv\Scripts\activate.ps1")) {
    Write-Host "[ERROR] .venv not found. Run: uv venv .venv" -ForegroundColor Red
    exit 1
}
Write-Host "[1/5] Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

# ── Alembic Migrations ─────────────────────────────────────────────────────
Write-Host "[2/5] Running Alembic migrations (alembic upgrade head)..."
alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Migration failed — check DATABASE_URL in .env" -ForegroundColor Red
    exit 1
}
Write-Host "       Migrations: OK" -ForegroundColor Green

# ── Seed Demo Data ─────────────────────────────────────────────────────────
Write-Host "[3/5] Seeding synthetic demo data (idempotent)..."
python data\seed_demo_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Demo data seed failed — continuing anyway" -ForegroundColor Yellow
}

# ── Frontend Build Check ────────────────────────────────────────────────────
Write-Host "[4/5] Checking frontend dev server readiness..."
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "       Installing frontend dependencies (npm install)..."
    Push-Location frontend
    npm install --silent
    Pop-Location
}

# ── Start Servers ───────────────────────────────────────────────────────────
Write-Host "[5/5] Starting backend (port 8000) and frontend (port 5173)..."
Write-Host ""
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop all processes." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Start backend in background
$backend = Start-Process -FilePath ".venv\Scripts\uvicorn.exe" `
    -ArgumentList "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" `
    -PassThru -NoNewWindow

# Start frontend dev server
Push-Location frontend
npm run dev
Pop-Location

# Cleanup on exit
if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Dev stack stopped." -ForegroundColor Yellow
