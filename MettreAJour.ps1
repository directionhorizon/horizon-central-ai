# HORIZON CENTRAL AI — mise a jour locale (bouton "Mettre a jour").
# Recupere le code depuis GitHub puis recompile l'interface servie par le moteur
# local (dist/). Aucune donnee n'est supprimee : la base SQLite reste intacte.
# Parametre -NoPause : ne pas attendre une touche (usage automatise).
param([switch]$NoPause)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$branch = 'main'

function Pause-Exit([int]$code) {
    if (-not $NoPause) {
        Write-Host ''
        Read-Host "Appuyez sur Entree pour fermer"
    }
    exit $code
}

Write-Host "HORIZON CENTRAL AI - mise a jour locale" -ForegroundColor Cyan
Write-Host "Dossier : $root" -ForegroundColor DarkGray

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git est introuvable sur ce PC : mise a jour impossible." -ForegroundColor Red
    Pause-Exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $root '.git'))) {
    Write-Host "Ce dossier n'est pas une copie Git de HORIZON (pas de .git)." -ForegroundColor Yellow
    Write-Host "Utilisez le depot source, ou recuperez la version a jour depuis GitHub." -ForegroundColor Yellow
    Pause-Exit 1
}

Push-Location $root
try {
    Write-Host "1/3  Recuperation des changements (git fetch / pull)..." -ForegroundColor Cyan
    git fetch --quiet origin 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Echec de la connexion a GitHub (pas d'acces reseau ?)." -ForegroundColor Red
        Pause-Exit 1
    }

    $before = (git rev-parse HEAD).Trim()
    git pull --ff-only --quiet origin $branch 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Le 'git pull' a echoue (modifications locales ou divergence)." -ForegroundColor Red
        Pause-Exit 1
    }
    $after = (git rev-parse HEAD).Trim()

    if ($before -eq $after) {
        Write-Host "Deja a jour : aucun nouveau code." -ForegroundColor Green
        Write-Host "Si l'interface semble ancienne, faites Ctrl+F5 dans la fenetre HORIZON." -ForegroundColor DarkGray
        Pause-Exit 0
    }
    Write-Host ("Nouveau code : " + $before.Substring(0,7) + " -> " + $after.Substring(0,7)) -ForegroundColor Green

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Host "npm (Node.js) introuvable : impossible de recompiler l'interface." -ForegroundColor Red
        Pause-Exit 1
    }

    $lockChanged = git diff --name-only $before $after -- package-lock.json
    if ($lockChanged) {
        Write-Host "2/3  Dependances modifiees : installation (npm ci)..." -ForegroundColor Cyan
        npm ci
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Echec de 'npm ci'." -ForegroundColor Red
            Pause-Exit 1
        }
    } else {
        Write-Host "2/3  Dependances inchangees : installation ignoree." -ForegroundColor DarkGray
    }

    Write-Host "3/3  Recompilation de l'interface (npm run build)..." -ForegroundColor Cyan
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Echec de la compilation de l'interface." -ForegroundColor Red
        Pause-Exit 1
    }

    Write-Host "Mise a jour terminee." -ForegroundColor Green
    Write-Host "Faites Ctrl+F5 dans la fenetre HORIZON (ou relancez HORIZON.bat)." -ForegroundColor DarkGray
    Pause-Exit 0
}
finally {
    Pop-Location
}
