$ErrorActionPreference = "Stop"
$root = (Resolve-Path "..").Path
$env:NEGAO_API_URL = "http://127.0.0.1:8766"
$env:NEGAO_WS_URL = "ws://127.0.0.1:8766"
$env:NEGAO_SERVICE_API_KEY = "test-only-service"
$outLog = Join-Path (Get-Location) "voice-v1-frontend.out.log"
$errLog = Join-Path (Get-Location) "voice-v1-frontend.err.log"
$process = Start-Process `
    -FilePath "npm.cmd" `
    -WorkingDirectory (Get-Location).Path `
    -ArgumentList @("run", "dev", "--", "-H", "127.0.0.1", "-p", "3000") `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru
$ready = $false
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    Start-Sleep -Milliseconds 300
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:3000/login"
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # O Next pode ainda estar compilando a rota inicial.
    }
}
Write-Output "VOICE_FRONTEND_PID=$($process.Id)"
Write-Output "VOICE_FRONTEND_READY=$([int]$ready)"
if (-not $ready -and -not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
}
if (-not $ready) { exit 1 }
