# Run every PatternGuard test. Usage (from the repository root):
#   powershell -ExecutionPolicy Bypass -File tests\run_all.ps1
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

$results = @()
function Invoke-Step($name, $exe, $argList) {
    Write-Host "=== $name ==="
    & $exe @argList
    $code = $LASTEXITCODE
    $script:results += [pscustomobject]@{ Test = $name; ExitCode = $code; Status = $(if ($code -eq 0) { 'PASS' } else { 'FAIL' }) }
}

$steps = @(
    @('Unit tests (Node)', 'node', @('tests\unit.test.js')),
    @('Regression (browser)', $py, @('tests\regression.py')),
    @('Config change test (TC-H05)', $py, @('tests\config_test.py')),
    @('Report test cases', $py, @('tests\report_cases.py'))
)
foreach ($s in $steps) {
    $file = $s[2][0]
    if (Test-Path $file) { Invoke-Step $s[0] $s[1] $s[2] } else { Write-Host "skip: $file not present" }
}

Write-Host ''
$results | Format-Table -AutoSize
if ($results | Where-Object { $_.ExitCode -ne 0 }) { exit 1 } else { exit 0 }
