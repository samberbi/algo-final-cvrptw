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
    & $projectPython -c "import struct,sys; sys.exit(0 if sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8 else 'Python 3.12 en 64 bits requis.')"
    if ($LASTEXITCODE -ne 0) { throw 'Recreer .venv sur ce PC avec Python 3.12 en 64 bits. Consulter DEMARRAGE_WINDOWS11.md.' }
    if (-not $VerifierSeulement) {
        $installationArguments = @('-m','pip','install','-r','requirements-reference-final.txt')
        $constraints = 'results/terminal_comparison/CONTRAINTES_INSTALLATION_LOCALE.txt'
        if (Test-Path -LiteralPath $constraints) { $installationArguments += @('-c',$constraints) }
        & $projectPython @installationArguments
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
