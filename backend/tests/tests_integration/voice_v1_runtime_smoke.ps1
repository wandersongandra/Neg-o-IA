param(
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"

function Read-RootEnvValue {
    param([string]$Name, [string]$Root)

    $line = Get-Content -LiteralPath (Join-Path $Root ".env") |
        Where-Object { $_ -match "^$Name=" } |
        Select-Object -First 1
    if ($null -eq $line) {
        return ""
    }
    return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$env:NEGAO_ENV = "test"
$env:NEGAO_REGISTRATION_ENABLED = "true"
$env:NEGAO_DATABASE_URL = "postgresql+asyncpg://sophie_foundation_05:SophieTest2026Local@127.0.0.1:55432/sophie_foundation_05"
$env:NEGAO_REDIS_URL = "redis://127.0.0.1:6380/14"
$env:NEGAO_SECRET_KEY = "test-only-local"
$env:NEGAO_SERVICE_API_KEY = "test-only-service"
$env:NEGAO_CORS_ORIGINS = '["http://127.0.0.1:3000"]'
$env:NEGAO_NVIDIA_API_KEY = Read-RootEnvValue -Name "NEGAO_NVIDIA_API_KEY" -Root $root
$env:NEGAO_NVIDIA_BASE_URL = Read-RootEnvValue -Name "NEGAO_NVIDIA_BASE_URL" -Root $root

$outLog = Join-Path $root "backend\voice-v1-runtime.out.log"
$errLog = Join-Path $root "backend\voice-v1-runtime.err.log"
$python = Join-Path $root "backend\.venv\Scripts\python.exe"
$process = Start-Process `
    -FilePath $python `
    -WorkingDirectory (Join-Path $root "backend") `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru

$ready = $false
$lastBody = ""
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    Start-Sleep -Milliseconds 300
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/health/ready"
        $lastBody = $response.Content
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        if ($_.ErrorDetails.Message) {
            $lastBody = $_.ErrorDetails.Message
        }
    }
}

Write-Output "VOICE_BACKEND_PID=$($process.Id)"
Write-Output "VOICE_BACKEND_READY=$([int]$ready)"
if (-not $ready -and $lastBody) {
    Write-Output "VOICE_BACKEND_READY_BODY=$lastBody"
}
if (-not $ready) {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    exit 1
}
