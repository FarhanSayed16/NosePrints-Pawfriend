# Cloud Run deploy helper for NosePrints (Windows PowerShell).
# Prerequisites: gcloud CLI, Docker Desktop running, ONNX models under backend/models/,
# durable S3_* env vars for photos, Supabase DATABASE_URL.
# See docs/DEPLOY.md and docs/NATIONWIDE_READINESS_ROADMAP.md.

param(
    [string]$ProjectId = "",
    [string]$Region = "us-central1",
    [string]$Service = "noseprints",
    [string]$EnvFile = ".env.cloudrun.yaml"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== NosePrints Cloud Run deploy ==" -ForegroundColor Cyan

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Error "gcloud not found. Install Google Cloud SDK, then re-run."
}

$detector = Join-Path $Root "backend\models\nose_detector.onnx"
$embed = Join-Path $Root "backend\models\embedding_model.onnx"
if (-not (Test-Path $detector) -or -not (Test-Path $embed)) {
    Write-Error "Missing ONNX models under backend/models/. Bundle from the machine that has them."
}

if (-not $ProjectId) {
    $ProjectId = (gcloud config get-value project 2>$null).Trim()
}
if (-not $ProjectId -or $ProjectId -eq "(unset)") {
    Write-Error "Set -ProjectId or run: gcloud config set project YOUR_PROJECT"
}

Write-Host "Project: $ProjectId  Region: $Region  Service: $Service"

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project $ProjectId

$deployArgs = @(
    "run", "deploy", $Service,
    "--source", ".",
    "--region", $Region,
    "--project", $ProjectId,
    "--allow-unauthenticated",
    "--memory", "2Gi",
    "--cpu", "1",
    "--timeout", "300",
    "--set-env-vars", "SERVE_FRONTEND=true,DEBUG=false,FRONTEND_DIR=/app/frontend_dist"
)

if (Test-Path (Join-Path $Root $EnvFile)) {
    Write-Host "Using env vars file: $EnvFile"
    $deployArgs += @("--env-vars-file", $EnvFile)
} else {
    Write-Warning "No $EnvFile found. Pass DATABASE_URL / JWT / S3_* via Cloud Console or create the YAML file."
}

& gcloud @deployArgs

Write-Host ""
Write-Host "Next:" -ForegroundColor Green
Write-Host "  1. Map custom domain id.pawfriend.in (Cloud Run domain mapping)"
Write-Host "  2. Set PUBLIC_APP_URL to that HTTPS origin"
Write-Host "  3. Confirm /health shows database=connected and storage=s3 (or your mode)"
Write-Host "  4. Retire local Cloudflare tunnel for public traffic"
