param(
    [string]$BaseUrl = "http://127.0.0.1:8766",
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"

function Start-SophieRuntime {
    param([string]$Root)

    $pgPass = (wsl.exe -d Ubuntu -u root -- cat /tmp/sophie_foundation_05_db_password).Trim()
    if ([string]::IsNullOrWhiteSpace($pgPass)) {
        throw "dedicated test DB password unavailable"
    }

    $env:NEGAO_ENV = "test"
    $env:NEGAO_REGISTRATION_ENABLED = "true"
    $env:NEGAO_DATABASE_URL = "postgresql+asyncpg://sophie_foundation_05:$pgPass@127.0.0.1:55432/sophie_foundation_05"
    $env:NEGAO_REDIS_URL = "redis://127.0.0.1:6380/14"
    $env:NEGAO_SECRET_KEY = "test-only-local"
    $env:NEGAO_SERVICE_API_KEY = "test-only-service"
    $env:NEGAO_API_KEY = "test-only-api"
    $env:NEGAO_CORS_ORIGINS = '["http://127.0.0.1:3000"]'
    $env:NEGAO_NVIDIA_API_KEY = ""

    Start-Process `
        -FilePath "$Root\backend\.venv\Scripts\python.exe" `
        -WorkingDirectory "$Root\backend" `
        -ArgumentList @(
            "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port"
        ) `
        -RedirectStandardOutput "$Root\backend\runtime-restart-probe.out.log" `
        -RedirectStandardError "$Root\backend\runtime-restart-probe.err.log" |
        Out-Null
}

function Wait-Ready {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 300
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/health/ready"
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            # O processo ainda está iniciando ou a dependência ainda não respondeu.
        }
    }
    return $false
}

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$suffix = [guid]::NewGuid().ToString("N").Substring(0, 10)
$username = "foundation-restart-$suffix"
$password = "Restart-runtime-password-2026!"
$registerBody = @{ username = $username; password = $password; display_name = "Restart Proof" } |
    ConvertTo-Json
$register = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/security/register" `
    -ContentType "application/json" `
    -Body $registerBody
$loginBody = @{ username = $username; password = $password } | ConvertTo-Json
$login = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/security/login" `
    -ContentType "application/json" `
    -Body $loginBody
$headers = @{ Authorization = "Bearer $($login.access_token)" }
$conversation = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/conversation/sessions" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body "{}"
$conversationId = $conversation.session_id
$marker = "restart-persistence-$suffix"
Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/conversation/sessions/$conversationId/messages" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body (@{ text = $marker } | ConvertTo-Json) | Out-Null

$listeners = Get-NetTCPConnection -State Listen -LocalPort $Port
foreach ($listener in $listeners) {
    Stop-Process -Id $listener.OwningProcess -Force
}
Start-Sleep -Seconds 1
Start-SophieRuntime -Root $root
$readyAfterRestart = Wait-Ready
if (-not $readyAfterRestart) {
    throw "API did not become ready after restart"
}

$loginAfterRestart = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/security/login" `
    -ContentType "application/json" `
    -Body $loginBody
$headersAfterRestart = @{ Authorization = "Bearer $($loginAfterRestart.access_token)" }
$history = Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/conversation/sessions/$conversationId/messages" `
    -Headers $headersAfterRestart
$persisted = @($history.messages | Where-Object { $_.content -eq $marker }).Count -gt 0

Write-Output "RESTART_READY=$([int]$readyAfterRestart)"
Write-Output "RESTART_PERSISTED=$([int]$persisted)"
Write-Output "RESTART_HISTORY_STATUS=200"
Write-Output "RESTART_OWNER_VALIDATED=$([int]($conversation.user_id -eq $loginAfterRestart.user_id))"
