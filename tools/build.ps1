$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    & .venv\Scripts\python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend checks failed.' }
    & npm.cmd test
    if ($LASTEXITCODE -ne 0) { throw 'Avatar checks failed.' }
    & node.exe tools/audit_motion.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Actual VRM joint audit failed.' }
    & .venv\Scripts\python.exe tools/collect_notices.py
    if ($LASTEXITCODE -ne 0) { throw 'License inventory failed.' }
    & .venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath build/engine --workpath build/pyinstaller tools/clinic-engine.spec
    if ($LASTEXITCODE -ne 0) { throw 'Engine packaging failed.' }
    & npm.cmd run package
    if ($LASTEXITCODE -ne 0) { throw 'Desktop packaging failed.' }
    & .venv\Scripts\python.exe tools/release_receipt.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaged file verification failed.' }
    $packageConfig = Get-Content -LiteralPath package.json -Raw | ConvertFrom-Json
    Write-Host "Created $($packageConfig.build.directories.output)/win-unpacked/VSL Clinic.exe. Keep the entire folder together."
}
finally {
    Pop-Location
}
