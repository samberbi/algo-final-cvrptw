param([switch]$VerifierSeulement)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectDirectory '.venv\Scripts\python.exe'
Push-Location -LiteralPath $projectDirectory
try {
    if (-not (Test-Path -LiteralPath $projectPython)) {
        if ($VerifierSeulement) { throw 'Environnement absent : lancer INSTALLER.ps1 sans -VerifierSeulement.' }
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Installer Python 3.12 en 64 bits et son lanceur py.' }
    }
    if (-not $VerifierSeulement) {
        & $projectPython -m pip install -r requirements-reference-final.txt
        if ($LASTEXITCODE -ne 0) { throw 'Installation incomplete : lire le message de pip.' }
    }
    & $projectPython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependances incoherentes.' }
    & $projectPython -c "from scripts.run_benchmark import check_environment; print(check_environment(['ils', 'size_based'], plots=True))"
    if ($LASTEXITCODE -ne 0) { throw 'Le Python local ne fournit pas tous les moteurs requis.' }
    Write-Host 'Environnement statique pret. Consulter le README de ce dossier pour les tests.'
} finally {
    Pop-Location
}
