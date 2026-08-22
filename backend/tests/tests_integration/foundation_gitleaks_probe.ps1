$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

$roots = @(
    "backend/app",
    "backend/tests",
    "frontend/app",
    "frontend/.next",
    "docs/sophie",
    ".github",
    "frontend/package.json",
    "frontend/package-lock.json",
    "backend/pyproject.toml"
)
$currentTotal = 0
$buildArtifactTotal = 0

foreach ($root in $roots) {
    $report = Join-Path $env:TEMP ("sophie-gitleaks-current-" + [guid]::NewGuid().ToString("N") + ".json")
    try {
        & gitleaks dir --redact --no-banner --exit-code 0 --report-format json --report-path $report $root 2>$null | Out-Null
        $count = 0
        if (Test-Path -LiteralPath $report) {
            $data = Get-Content -Raw -LiteralPath $report | ConvertFrom-Json
            if ($null -ne $data) {
                $count = @($data).Count
            }
        }
        if ($root -eq "frontend/.next") {
            $buildArtifactTotal += $count
        }
        else {
            $currentTotal += $count
        }
        Write-Output "CURRENT_ROOT=$root;FINDINGS=$count"
    }
    finally {
        Remove-Item -LiteralPath $report -Force -ErrorAction SilentlyContinue
    }
}

$historyReport = Join-Path $env:TEMP ("sophie-gitleaks-history-" + [guid]::NewGuid().ToString("N") + ".json")
try {
    & gitleaks git --redact --no-banner --exit-code 0 --report-format json --report-path $historyReport --log-opts="--all" . 2>$null | Out-Null
    $historyCount = 0
    if (Test-Path -LiteralPath $historyReport) {
        $historyData = Get-Content -Raw -LiteralPath $historyReport | ConvertFrom-Json
        if ($null -ne $historyData) {
            $historyCount = @($historyData).Count
        }
    }
    Write-Output "CURRENT_SOURCE_FINDINGS=$currentTotal"
    Write-Output "BUILD_ARTIFACT_FINDINGS=$buildArtifactTotal"
    Write-Output "HISTORY_FINDINGS=$historyCount"
}
finally {
    Remove-Item -LiteralPath $historyReport -Force -ErrorAction SilentlyContinue
}
