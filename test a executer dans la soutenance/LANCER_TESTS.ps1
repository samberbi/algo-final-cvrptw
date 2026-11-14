param(
    [ValidateSet('SixFamilles','Toutes100','Toutes1000','Selection')]
    [string]$Mode = 'SixFamilles',
    [double]$Seconds = 0,
    [int]$Seed = 4101,
    [int]$Workers = 1
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Executer INSTALLER.ps1 dans ce dossier, ou suivre sa procedure Python manuelle.'
}
$testArguments = @('-X','utf8','scripts/test_instances.py')
switch ($Mode) {
    'SixFamilles' { $testArguments += @('--instances','C101','C201','R101','R201','RC101','RC201') }
    'Toutes100' { $testArguments += @('--all','--sizes','100','--label','comparaison_100') }
    'Toutes1000' { $testArguments += @('--all','--sizes','1000','--label','comparaison_1000') }
    'Selection' { $testArguments += @('--all','--sizes','100','1000','--dry-run') }
}
if ($Seconds -eq 0) { $Seconds = if ($Mode -eq 'Toutes1000') { 30 } else { 5 } }
$testArguments += @('--seconds',$Seconds,'--seeds',$Seed,'--workers',$Workers)
Push-Location -LiteralPath $projectDirectory
try {
    & $projectPython @testArguments
    if ($LASTEXITCODE -ne 0) { throw 'La commande a signale un echec : consulter le statut et les resultats sauvegardes.' }
} finally {
    Pop-Location
}
