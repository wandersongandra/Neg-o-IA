param(
    [string]$BaseUrl = "http://127.0.0.1:8767",
    [int]$Port = 8767
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$envFile = Join-Path $root ".env"
$logOut = Join-Path $env:TEMP "sophie-foundation-legacy-key.out.log"
$logErr = Join-Path $env:TEMP "sophie-foundation-legacy-key.err.log"
$server = $null

function Get-HttpStatus {
    param(
        [string]$Uri,
        [hashtable]$Headers
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Method Get -Uri $Uri -Headers $Headers
        return [int]$response.StatusCode
    }
    catch {
        return [int]$_.Exception.Response.StatusCode.value__
    }
}

try {
    $legacyLine = Get-Content -LiteralPath $envFile |
        Where-Object { $_ -match '^\s*NEGAO_API_KEY=' } |
        Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($legacyLine)) {
        throw "NEGAO_API_KEY not found in local environment file"
    }
    $legacyKey = ($legacyLine -split "=", 2)[1].Trim().Trim('"').Trim("'")
    if ([string]::IsNullOrWhiteSpace($legacyKey)) {
        throw "NEGAO_API_KEY is empty"
    }

    $pgPass = $env:SOPHIE_FOUNDATION_TEST_DB_PASSWORD
    if ([string]::IsNullOrWhiteSpace($pgPass)) {
        throw "dedicated test DB password unavailable"
    }

    # Processo isolado: a credencial legada é lida somente em memória e nunca
    # é escrita em saída, log, fixture ou argumento de processo.
    $env:NEGAO_ENV = "production"
    $env:NEGAO_REGISTRATION_ENABLED = "false"
    $env:NEGAO_DATABASE_URL = "postgresql+asyncpg://sophie_foundation_05:$pgPass@127.0.0.1:55432/sophie_foundation_05"
    $env:NEGAO_REDIS_URL = "redis://127.0.0.1:6380/14"
    $env:NEGAO_SECRET_KEY = "test-only-production-secret-" + ("x" * 48)
    $env:NEGAO_SERVICE_API_KEY = "test-only-production-service-" + ("x" * 48)
    $env:NEGAO_CORS_ORIGINS = '["http://127.0.0.1:3000"]'
    $env:NEGAO_NVIDIA_API_KEY = ""
    $env:NEGAO_API_KEY = $legacyKey

    $server = Start-Process `
        -FilePath "$root\backend\.venv\Scripts\python.exe" `
        -WorkingDirectory "$root\backend" `
        -ArgumentList @(
            "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port"
        ) `
        -RedirectStandardOutput $logOut `
        -RedirectStandardError $logErr `
        -PassThru

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 300
        try {
            if ((Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/health/ready").StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch {
            # O processo ainda está inicializando.
        }
    }
    if (-not $ready) {
        throw "isolated production runtime did not become ready"
    }

    $headers = @{ "X-API-Key" = $legacyKey }
    $securityStatus = Get-HttpStatus -Uri "$BaseUrl/security/status" -Headers $headers
    $databaseStatus = Get-HttpStatus -Uri "$BaseUrl/database/status" -Headers $headers
    Write-Output "LEGACY_KEY_SECURITY_STATUS=$securityStatus"
    Write-Output "LEGACY_KEY_SERVICE_STATUS=$databaseStatus"
}
finally {
    if ($null -ne $server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $logOut, $logErr -Force -ErrorAction SilentlyContinue
}
