param(
    [string]$Python = '',
    [string]$Instance = 'C101',
    [int]$Size = 25,
    [double]$Seconds = 5,
    [ValidateSet('size_based','construction','ils','sa','pyvrp','hybrid','refined','refined_ils','refined_no_partition','ortools')]
    [string]$Method = 'size_based'
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $projectPython = Join-Path $projectDirectory '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $projectPython) {
        $Python = $projectPython
    } else {
        $Python = (Get-Command python -ErrorAction Stop).Source
    }
}
Push-Location -LiteralPath $projectDirectory
try {
    & $Python -X utf8 scripts/test_instances.py --instances $Instance --size $Size --seconds $Seconds --method $Method --show-routes --label soutenance_demo
    if ($LASTEXITCODE -ne 0) {
        throw 'La commande a signalé un échec. Lire le statut et le dossier sauvegardé dans le terminal.'
    }
} finally {
    Pop-Location
}
