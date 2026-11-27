# HORIZON CENTRAL AI — lanceur d'application de bureau (Offline-First)
# Usage : clic droit > Executer avec PowerShell, ou double-clic sur HORIZON.bat
#
# Principe : le backend FastAPI sert lui-meme l'interface compilee (dist/) et la
# base SQLite locale. Aucune connexion Internet n'est necessaire pour demarrer.
# La fenetre est ouverte en mode application (sans barre d'adresse) via Edge ou
# Chrome deja installes : aucun paquet supplementaire n'est requis.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$dist = Join-Path $root 'dist\index.html'
$baseUrl = 'http://127.0.0.1:8000'

function Test-Port([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

# --- Mode HYBRIDE (B) : HORIZON EN LIGNE d'abord ; le local n'est qu'un secours.
# Le serveur en ligne fait foi (meme version, memes donnees) : aucune mise a jour
# a gerer sur ce PC. Si Internet manque, on demarre le moteur local hors ligne.
$onlineUrl = 'https://horizon.mayela-crm.com'
$browsers = @(
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
)
$windowFlags = @(
    '--no-first-run',
    '--no-default-browser-check',
    '--start-maximized',
    '--window-size=1500,950',
    '--disable-features=msEdgeSleepingTabs,SleepingTabs,CalculateNativeWinOcclusion',
    '--disable-background-timer-throttling',
    '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows'
)
function Open-AppWindow([string]$url, [string]$profile) {
    if (-not (Test-Path -LiteralPath $profile)) {
        New-Item -ItemType Directory -Path $profile -Force | Out-Null
    }
    $engine = $browsers | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($engine) {
        Start-Process -FilePath $engine -ArgumentList (@("--app=$url", "--user-data-dir=$profile") + $windowFlags) | Out-Null
        return $true
    }
    Start-Process $url | Out-Null
    return $false
}

$mode = 'online'   # 'online' = A (serveur en ligne uniquement) ; 'hybride' = B (local en secours)

$online = $false
try {
    $probe = Invoke-WebRequest -Uri "$onlineUrl/api/v1/health" -UseBasicParsing -TimeoutSec 5
    if ($probe.StatusCode -eq 200) { $online = $true }
} catch { $online = $false }

if ($online) {
    Write-Host "HORIZON CENTRAL AI - EN LIGNE ($onlineUrl)" -ForegroundColor Green
    Open-AppWindow $onlineUrl (Join-Path $env:LOCALAPPDATA 'HORIZON\browser-profile-online') | Out-Null
    Write-Host "Source de verite : le serveur en ligne. Aucune mise a jour a gerer ici." -ForegroundColor DarkGray
    exit 0
}

if ($mode -eq 'online') {
    # Mode A : aucune copie locale. On explique clairement, sans rien inventer.
    Write-Host "Serveur en ligne injoignable : $onlineUrl" -ForegroundColor Red
    $errorPage = Join-Path $root 'desktop\desktop-error.html'
    if (Test-Path -LiteralPath $errorPage) {
        $fileUrl = 'file:///' + ($errorPage -replace '\\', '/')
        $reason = "Impossible de joindre le serveur en ligne ($onlineUrl). Verifiez la connexion Internet, puis relancez HORIZON."
        $query = '?title=' + [uri]::EscapeDataString('HORIZON CENTRAL AI -- serveur en ligne injoignable') +
            '&reason=' + [uri]::EscapeDataString($reason) +
            '&app=' + [uri]::EscapeDataString($onlineUrl)
        Open-AppWindow "$fileUrl$query" (Join-Path $env:LOCALAPPDATA 'HORIZON\browser-profile-online') | Out-Null
    }
    exit 1
}

Write-Host "Pas d'acces a $onlineUrl : demarrage du moteur LOCAL (mode hors ligne)." -ForegroundColor Yellow

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Environnement Python absent : $python" -ForegroundColor Red
    Write-Host "Creer le venv et installer backend\requirements.txt." -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour fermer"
    exit 1
}

if (-not (Test-Path -LiteralPath $dist)) {
    Write-Host "Interface compilee absente : $dist" -ForegroundColor Yellow
    Write-Host "Executer 'npm run build' dans $root avant de relancer." -ForegroundColor Yellow
}

if (-not (Test-Port 8000)) {
    Write-Host "Demarrage du moteur local HORIZON CENTRAL AI..." -ForegroundColor Cyan
    Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory $backend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $backend 'backend_out.log') `
        -RedirectStandardError (Join-Path $backend 'backend_err.log') | Out-Null
}

$engineReady = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $health = Invoke-WebRequest -Uri "$baseUrl/api/v1/health" -UseBasicParsing -TimeoutSec 3
        if ($health.StatusCode -eq 200) { $engineReady = $true; break }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

# L'API peut repondre alors que l'interface compilee n'est pas servie : on
# verifie aussi le shell HTML avant d'ouvrir la fenetre (sinon ecran vide).
$uiReady = $false
if ($engineReady) {
    for ($i = 0; $i -lt 20; $i++) {
        try {
            $page = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing -TimeoutSec 3
            if ($page.StatusCode -eq 200 -and $page.Content -match 'id="root"') { $uiReady = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 400
    }
}

$failureReason = ''
if (-not $engineReady) {
    $failureReason = "Le moteur local n'a pas repondu sur $baseUrl (port 8000). Consultez backend\backend_err.log."
} elseif (-not $uiReady) {
    $failureReason = "Le moteur repond mais l'interface compilee (dist) n'est pas servie. Executer 'npm run build' dans le dossier du projet, puis relancer."
}

$profileDir = Join-Path $env:LOCALAPPDATA 'HORIZON\browser-profile'
if (-not (Test-Path -LiteralPath $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

$browsers = @(
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
)
$browser = $browsers | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

# Anti-cache : le shell HTML n'est pas mis en cache par le backend, mais on
# ajoute la version courante en parametre pour forcer un chargement frais.
$version = 'dev'
try {
    $desktop = Invoke-RestMethod -Uri "$baseUrl/api/v1/system/desktop" -TimeoutSec 5
    if ($desktop.version) { $version = [string]$desktop.version }
} catch { }
$appUrl = "$baseUrl/?v=$version"
$errorPage = Join-Path $root 'desktop\desktop-error.html'

# La fenetre n'est jamais ouverte vide : si le moteur ou l'interface manque,
# une page d'erreur locale explicite est affichee (aucune dependance reseau).
$targetUrl = $appUrl
if ($failureReason) {
    Write-Host $failureReason -ForegroundColor Red
    if (Test-Path -LiteralPath $errorPage) {
        $fileUrl = 'file:///' + ($errorPage -replace '\\', '/')
        $query = '?title=' + [uri]::EscapeDataString('HORIZON CENTRAL AI — interface indisponible') +
            '&reason=' + [uri]::EscapeDataString($failureReason) +
            '&app=' + [uri]::EscapeDataString($appUrl) +
            '&log=' + [uri]::EscapeDataString((Join-Path $backend 'backend_err.log'))
        $targetUrl = "$fileUrl$query"
        Write-Host "Ecran d'erreur local affiche dans la fenetre." -ForegroundColor Yellow
    } else {
        Write-Host "Ecran d'erreur local introuvable : $errorPage" -ForegroundColor Red
    }
}

# Options de fiabilite de la fenetre de bureau :
#  - msEdgeSleepingTabs : empeche la mise en veille prolongee de la page
#    (c'est cette mise en veille qui vidait la fenetre en laissant le titre) ;
#  - CalculateNativeWinOcclusion / backgrounding : la page n'est pas dechargee
#    quand la fenetre est partiellement masquee ;
#  - taille et position explicites pour eviter une fenetre minuscule.
$windowFlags = @(
    '--no-first-run',
    '--no-default-browser-check',
    '--start-maximized',
    '--window-size=1500,950',
    '--disable-features=msEdgeSleepingTabs,SleepingTabs,CalculateNativeWinOcclusion',
    '--disable-background-timer-throttling',
    '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows'
)

if ($browser) {
    if ($failureReason) {
        Write-Host "Ouverture de la fenetre HORIZON CENTRAL AI (ecran d'erreur)..." -ForegroundColor Yellow
    } else {
        Write-Host "Ouverture de la fenetre HORIZON CENTRAL AI (mode application, version $version)..." -ForegroundColor Green
    }
    $arguments = @("--app=$targetUrl", "--user-data-dir=$profileDir") + $windowFlags
    Start-Process -FilePath $browser -ArgumentList $arguments | Out-Null
} else {
    Write-Host "Aucun navigateur Chromium detecte : ouverture dans le navigateur par defaut." -ForegroundColor Yellow
    Start-Process $targetUrl | Out-Null
}

if ($failureReason) {
    Write-Host "L'interface n'est pas disponible : corrigez la cause ci-dessus puis relancez HORIZON.bat." -ForegroundColor Yellow
} else {
    Write-Host "HORIZON CENTRAL AI est disponible sur $baseUrl" -ForegroundColor Green
}
Write-Host "Les donnees locales restent dans backend\data\horizon.db" -ForegroundColor DarkGray
Write-Host "Fermer cette fenetre ne coupe pas le moteur ; utiliser HORIZON-Stop.ps1 pour l'arreter." -ForegroundColor DarkGray
