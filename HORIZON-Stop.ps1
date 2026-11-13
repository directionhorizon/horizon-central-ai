# HORIZON CENTRAL AI — arret propre du moteur local.
# Aucune donnee n'est supprimee : la base SQLite reste intacte sur le disque.
$ErrorActionPreference = 'Stop'

$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $conn) {
    Write-Host "Aucun moteur HORIZON n'ecoute sur 127.0.0.1:8000." -ForegroundColor Yellow
    exit 0
}

$process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
if (-not $process) {
    Write-Host "Processus introuvable pour le port 8000." -ForegroundColor Yellow
    exit 0
}

Write-Host "Arret de $($process.ProcessName) (PID $($process.Id))..." -ForegroundColor Cyan
Stop-Process -Id $process.Id -Force
Start-Sleep -Seconds 2
Write-Host "Moteur arrete. Donnees conservees dans backend\data\horizon.db" -ForegroundColor Green
