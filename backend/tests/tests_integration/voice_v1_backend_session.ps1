$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$env:NEGAO_ENV = "test"
$env:NEGAO_REGISTRATION_ENABLED = "true"
$env:NEGAO_DATABASE_URL = "postgresql+asyncpg://sophie_foundation_05:SophieTest2026Local@127.0.0.1:55432/sophie_foundation_05"
$env:NEGAO_REDIS_URL = "redis://127.0.0.1:6380/14"
$env:NEGAO_SECRET_KEY = "test-only-local"
$env:NEGAO_SERVICE_API_KEY = "test-only-service"
$env:NEGAO_CORS_ORIGINS = '["http://127.0.0.1:3000"]'
$env:NEGAO_NVIDIA_API_KEY = ""
$env:NEGAO_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
foreach ($line in (Get-Content -LiteralPath (Join-Path $root ".env"))) {
    if ($line -match "^NEGAO_NVIDIA_API_KEY=(.*)$") {
        $env:NEGAO_NVIDIA_API_KEY = $Matches[1].Trim().Trim('"').Trim("'")
    }
    if ($line -match "^NEGAO_NVIDIA_BASE_URL=(.*)$") {
        $env:NEGAO_NVIDIA_BASE_URL = $Matches[1].Trim().Trim('"').Trim("'")
    }
}
& (Join-Path $root "backend\.venv\Scripts\python.exe") -m uvicorn app.main:app --host 127.0.0.1 --port 8766
