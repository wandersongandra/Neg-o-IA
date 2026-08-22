param(
    [string]$BaseUrl = "http://127.0.0.1:8766"
)

$ErrorActionPreference = "Stop"

function Get-HttpStatus {
    param(
        [ValidateSet("GET", "POST")][string]$Method,
        [string]$Uri,
        [hashtable]$Headers = @{},
        [string]$Body = $null
    )

    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Method $Method `
            -Uri $Uri `
            -Headers $Headers `
            -ContentType "application/json" `
            -Body $Body
        return [int]$response.StatusCode
    }
    catch {
        return [int]$_.Exception.Response.StatusCode.value__
    }
}

$suffix = [guid]::NewGuid().ToString("N").Substring(0, 10)
$username = "foundation-failure-$suffix"
$password = "Failure-runtime-password-2026!"
$credentials = @{ username = $username; password = $password; display_name = "Failure Probe" } |
    ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/security/register" `
    -ContentType "application/json" `
    -Body $credentials | Out-Null
$login = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/security/login" `
    -ContentType "application/json" `
    -Body (@{ username = $username; password = $password } | ConvertTo-Json)
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$readyBefore = Get-HttpStatus -Method GET -Uri "$BaseUrl/health/ready"
$createBefore = Get-HttpStatus `
    -Method POST `
    -Uri "$BaseUrl/conversation/sessions" `
    -Headers $headers `
    -Body "{}"
Write-Output "READY_BEFORE=$readyBefore"
Write-Output "PERSISTENCE_BEFORE=$createBefore"

& wsl.exe -d Ubuntu -- redis-cli -p 6380 shutdown nosave | Out-Null
Start-Sleep -Milliseconds 700
$redisDownLive = Get-HttpStatus -Method GET -Uri "$BaseUrl/health/live"
$redisDownReady = Get-HttpStatus -Method GET -Uri "$BaseUrl/health/ready"
$redisDownPersistence = Get-HttpStatus `
    -Method POST `
    -Uri "$BaseUrl/conversation/sessions" `
    -Headers $headers `
    -Body "{}"
Write-Output "REDIS_DOWN_LIVE=$redisDownLive"
Write-Output "REDIS_DOWN_READY=$redisDownReady"
Write-Output "REDIS_DOWN_PERSISTENCE=$redisDownPersistence"

& wsl.exe -d Ubuntu -- redis-server `
    --port 6380 `
    --bind 127.0.0.1 `
    --save "" `
    --appendonly no `
    --daemonize yes `
    --pidfile /tmp/sophie_foundation_05_redis.pid `
    --dir /tmp | Out-Null
Start-Sleep -Milliseconds 900
$redisRestoredReady = Get-HttpStatus -Method GET -Uri "$BaseUrl/health/ready"
$redisRestoredPersistence = Get-HttpStatus `
    -Method POST `
    -Uri "$BaseUrl/conversation/sessions" `
    -Headers $headers `
    -Body "{}"
Write-Output "REDIS_RESTORED_READY=$redisRestoredReady"
Write-Output "REDIS_RESTORED_PERSISTENCE=$redisRestoredPersistence"

& wsl.exe -d Ubuntu -u root -- pg_ctlcluster 16 sophie05 stop | Out-Null
Start-Sleep -Milliseconds 700
$dbDownLive = Get-HttpStatus -Method GET -Uri "$BaseUrl/health/live"
$dbDownReady = Get-HttpStatus -Method GET -Uri "$BaseUrl/health/ready"
$dbDownAuth = Get-HttpStatus `
    -Method GET `
    -Uri "$BaseUrl/security/status" `
    -Headers $headers
Write-Output "DB_DOWN_LIVE=$dbDownLive"
Write-Output "DB_DOWN_READY=$dbDownReady"
Write-Output "DB_DOWN_AUTH=$dbDownAuth"

& wsl.exe -d Ubuntu -u root -- pg_ctlcluster 16 sophie05 start | Out-Null
Start-Sleep -Milliseconds 1200
$dbRestoredReady = Get-HttpStatus -Method GET -Uri "$BaseUrl/health/ready"
$dbRestoredAuth = Get-HttpStatus `
    -Method GET `
    -Uri "$BaseUrl/security/status" `
    -Headers $headers
Write-Output "DB_RESTORED_READY=$dbRestoredReady"
Write-Output "DB_RESTORED_AUTH=$dbRestoredAuth"
