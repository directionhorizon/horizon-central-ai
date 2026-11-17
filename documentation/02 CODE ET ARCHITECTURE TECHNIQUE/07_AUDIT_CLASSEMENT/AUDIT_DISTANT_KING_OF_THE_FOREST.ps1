# =====================================================================
#  AUDIT DISTANT - INVENTAIRE DU PROJET "KING OF THE FOREST"
#  Politique de gouvernance des donnees v0.4 - etape 2 (audit distant)
#  LECTURE SEULE : aucun fichier deplace, modifie ou supprime.
#  Le seul ecrit est le rapport CSV dans $env:TEMP.
#  A executer SUR la Production Workstation, en PowerShell.
#    powershell -ExecutionPolicy Bypass -File .\AUDIT_DISTANT_KING_OF_THE_FOREST.ps1
# =====================================================================
param(
    [int]$Days = 180,
    [string[]]$Roots = $null,
    [string]$OutFile = (Join-Path $env:TEMP ("KOF_INVENTAIRE_" + (Get-Date -Format 'yyyyMMdd_HHmm') + ".csv"))
)

$ErrorActionPreference = 'SilentlyContinue'
$cutoff = (Get-Date).AddDays(-$Days)

Write-Host "=== AUDIT LECTURE SEULE - KING OF THE FOREST ===" -ForegroundColor Cyan
Write-Host "Machine : $env:COMPUTERNAME / utilisateur : $env:USERNAME"
Write-Host "Fenetre : fichiers modifies depuis le $($cutoff.ToString('yyyy-MM-dd'))"
Write-Host "Rapport : $OutFile`n"

# --- Racines candidates (on ne scanne que ce qui existe) ---
if ($Roots) {
    $roots = @($Roots | Where-Object { Test-Path -LiteralPath $_ })
} else {
    $roots = @(
        (Join-Path $env:USERPROFILE 'Desktop'),
        (Join-Path $env:USERPROFILE 'Documents'),
        (Join-Path $env:USERPROFILE 'Downloads'),
        (Join-Path $env:USERPROFILE 'OneDrive')
    )
    foreach ($d in @('D','E','F')) {
        $root = $d + ':'
        if (Get-PSDrive -Name $d -ErrorAction SilentlyContinue) { $roots += ($root + [char]92) }
    }
    $roots = @($roots | Where-Object { Test-Path -LiteralPath $_ })
}

# --- Exclusions : jamais de systeme, de caches, de dependances ---
$exclude = 'node_modules|\\AppData\\|\\Windows\\|Program Files|\.git\\|__pycache__|\.venv|site-packages|\$Recycle'

# --- Signatures de projet : nom explicite OU artefact de moteur de jeu ---
$namePattern  = 'forest|king of the|kof|gameforge|game.?forge'
$engineFiles  = @('*.uproject','*.uplugin','*.sln','*.unity','project.godot','*.blend','*.fbx','*.uasset','*.umap','*.pak')

Write-Host "1/3 - recherche par nom de projet..."
$byName = Get-ChildItem -LiteralPath $roots -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.LastWriteTime -ge $cutoff -and
        $_.FullName -notmatch $exclude -and
        $_.Name -match $namePattern
    }

Write-Host "2/3 - recherche par artefact de moteur de jeu..."
$engineScan = Get-ChildItem -LiteralPath $roots -Recurse -File -Include $engineFiles -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch $exclude }

$all = @($byName) + @($engineScan) | Sort-Object FullName -Unique

if (-not $all -or $all.Count -eq 0) {
    Write-Host "`nRESULTAT : aucun fichier correspondant." -ForegroundColor Yellow
    Write-Host "Interpretation : soit le projet n'est pas sur cette machine, soit il porte un autre nom."
    Write-Host "Action : communiquer les 3 dossiers les plus recents du disque de travail pour elargir la recherche."
} else {
    $all | Select-Object @{n='Chemin';e={$_.FullName}},
                         @{n='Taille_Ko';e={[math]::Round($_.Length/1KB,1)}},
                         LastWriteTime,
                         @{n='Type';e={ if ($_.Extension) { $_.Extension } else { '(sans)' } }} |
        Export-Csv -LiteralPath $OutFile -NoTypeInformation -Encoding UTF8

    Write-Host "`nRESULTAT : $($all.Count) fichiers correspondants." -ForegroundColor Green
    Write-Host "Rapport ecrit : $OutFile"
    Write-Host "`n--- 25 fichiers les plus recents ---"
    $all | Sort-Object LastWriteTime -Descending | Select-Object -First 25 | ForEach-Object {
        $ligne = $_.LastWriteTime.ToString('yyyy-MM-dd HH:mm') + '   ' + $_.Length + ' o   ' + $_.FullName
        Write-Host $ligne
    }

    Write-Host "`n--- Dossiers parents distincts (candidats 'racine du projet') ---"
    $all | ForEach-Object { $_.DirectoryName } | Sort-Object -Unique | Select-Object -First 20 |
        ForEach-Object { "  $_" }
}

Write-Host "`n3/3 - version des moteurs detectes (lecture seule) :"
foreach ($f in @('C:\Program Files\Unity\Hub\Editor','C:\Program Files\Epic Games','C:\Program Files\Godot')) {
    if (Test-Path -LiteralPath $f) { Write-Host "  present : $f" }
}
Write-Host "`n=== FIN - aucun fichier modifie. ===" -ForegroundColor Cyan
