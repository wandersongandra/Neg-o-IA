$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
$report = Join-Path $env:TEMP ("sophie-gitleaks-build-" + [guid]::NewGuid().ToString("N") + ".json")
try {
    & gitleaks dir --redact --no-banner --exit-code 0 --report-format json --report-path $report frontend/.next 2>$null | Out-Null
    if (-not (Test-Path -LiteralPath $report)) {
        Write-Output "BUILD_FINDINGS=0"
        exit 0
    }
    $data = Get-Content -Raw -LiteralPath $report | ConvertFrom-Json
    $findings = @($data)
    Write-Output "BUILD_FINDINGS=$($findings.Count)"
    foreach ($finding in $findings) {
        $file = [string]$finding.File
        $rule = [string]$finding.RuleID
        $line = [string]$finding.StartLine
        Write-Output "BUILD_FINDING_META=RULE:$rule;FILE:$file;LINE:$line"
    }
}
finally {
    Remove-Item -LiteralPath $report -Force -ErrorAction SilentlyContinue
}
