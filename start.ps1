# HORIZON CENTRAL AI — démarrage local (backend FastAPI + frontend Vite)
# Usage : powershell -ExecutionPolicy Bypass -File .\start.ps1
# Aucun secret n'est écrit ici : les clés restent dans backend\.env (ignoré par git).

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Environnement Python absent : $python" -ForegroundColor Red
    Write-Host "Créer le venv puis installer backend\requirements.txt avant de relancer." -ForegroundColor Yellow
    exit 1
}

function Test-Port([int]$port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

if (Test-Port 8000) {
    Write-Host "Backend déjà actif sur 127.0.0.1:8000" -ForegroundColor Yellow
} else {
    Write-Host "Démarrage du backend..." -ForegroundColor Cyan
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory $backend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $backend 'backend_out.log') `
        -RedirectStandardError (Join-Path $backend 'backend_err.log') | Out-Null
}

$port = 5173
while ((Test-Port $port) -and $port -lt 5185) { $port++ }
if ($port -ne 5173) {
    Write-Host "Port 5173 occupé : frontend sur $port" -ForegroundColor Yellow
    Write-Host "Ajouter http://localhost:$port à HORIZON_CORS_ORIGINS dans backend\.env" -ForegroundColor Yellow
}

Write-Host "Démarrage du frontend sur http://localhost:$port ..." -ForegroundColor Cyan
Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "npm run dev -- --port $port" -WorkingDirectory $root -WindowStyle Hidden

Start-Sleep -Seconds 8
try {
    $health = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 10 -UseBasicParsing
    Write-Host "Backend : $($health.StatusCode) $($health.Content)" -ForegroundColor Green
} catch {
    Write-Host "Backend injoignable : $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Frontend : http://localhost:$port" -ForegroundColor Green
Write-Host "Documentation : /api/docs (backend) · http://127.0.0.1:8000/docs" -ForegroundColor DarkGray
