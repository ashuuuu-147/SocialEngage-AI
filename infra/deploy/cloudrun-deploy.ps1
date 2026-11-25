<#
.SYNOPSIS
  Deploy SocialEngage AI FastAPI backend to Google Cloud Run (using gcloud CLI).
.EXAMPLE
  .\infra\deploy\cloudrun-deploy.ps1 -ProjectId "my-gcp-project" -Region "asia-south1"
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectId,

  [string]$Region = "asia-south1",
  [string]$ServiceName = "socialengage-api"
)

$ErrorActionPreference = "Stop"

Write-Host "Deploying $ServiceName to Google Cloud Run ($ProjectId / $Region)..." -ForegroundColor Cyan

gcloud config set project $ProjectId

gcloud run deploy $ServiceName `
  --source "services/api" `
  --region $Region `
  --platform managed `
  --allow-unauthenticated `
  --port 8000 `
  --min-instances 0 `
  --max-instances 3 `
  --set-env-vars "APP_ENV=production,DEV_AUTH_BYPASS=false,ENABLE_MOCK_SOURCES=false,AI_PROVIDER=gemini,AI_MODEL=gemini-2.5-flash"

Write-Host ""
Write-Host "Next: configure secrets in Cloud Run (DATABASE_URL, SUPABASE_URL, SUPABASE_JWT_SECRET, GEMINI_API_KEY, INTERNAL_JOB_SECRET, CORS_ORIGINS, WEB_APP_URL, TELEGRAM_BOT_TOKEN)." -ForegroundColor Yellow
