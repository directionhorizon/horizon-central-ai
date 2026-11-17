<#
  HORIZON CENTRAL AI - PHASE 3 - AUDIT DU PRODUCTION WORKSTATION
  ==============================================================
  SCRIPT DE LECTURE SEULE.

  - Ne modifie, ne deplace et ne supprime aucun fichier audite.
  - Ne lit aucun secret : seuls nom, chemin, taille, date et presence sont releves.
  - N'ouvre aucune connexion reseau. N'installe rien. Ne demarre aucun service.
  - Ecrit uniquement dans -OutDir (6 fichiers).

  Deux phases internes :
    Phase A - inventaire systeme (M12 a M17) : materiel, OS, logiciels, runtimes,
              outils IA, agents/MCP, conteneurs et virtualisation. Aucune racine.
    Phase B - decouverte automatique des racines techniques puis analyse des
              fichiers (M4 a M11), avec bornes de profondeur, duree et volume.

  Statuts utilises : FAIT OBSERVE / CANDIDAT / NON VERIFIE
  Le script ne qualifie JAMAIS un framework, un outil ou un projet comme
  systeme d'orchestration. Il produit des candidats avec leurs preuves ;
  la qualification finale est humaine.

  Version 1.1 - 2026-11-11
#>
[CmdletBinding()]
param(
    [string[]]$Roots = @(),

    [ValidateSet('Auto','Manuel')]
    [string]$Mode = 'Auto',

    [string]$OutDir = (Join-Path $env:TEMP ("HORIZON_AUDIT_PHASE3_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))),

    [int]$MaxMinutes = 20,
    [int]$MaxFiles = 200000,

    [switch]$IncludeAppData,
    [switch]$DiscoveryOnly,
    [switch]$AllowContainerInventory,
    [int]$VersionTimeoutSeconds = 5,

    [string[]]$ExtraSignatures = @()
)

$ErrorActionPreference = 'SilentlyContinue'

$script:ScriptVersion = '1.1'
$script:StartedAt     = Get-Date
$script:Deadline      = $script:StartedAt.AddMinutes($MaxMinutes)
$script:TimeBounded   = $false
$script:JournalPath   = $null
$script:ReportStatus  = 'COMPLET'
$script:ContainerEnv  = 'NON VERIFIE'
$script:FilesSeen     = 0
$script:EntriesSeen   = 0
$script:Limits        = New-Object System.Collections.Generic.List[string]
# R6 : liste separee des plafonds de collecte reellement atteints.
# Un plafond atteint => statut PARTIEL + entree journal + entree JSON + resume.
$script:Ceilings      = New-Object System.Collections.Generic.List[string]
$script:ReposBounded  = $false
$script:Errors        = New-Object System.Collections.Generic.List[string]
$script:Log           = New-Object System.Collections.Generic.List[string]
$script:Evidence      = New-Object System.Collections.Generic.List[object]
$script:Resources     = New-Object System.Collections.Generic.List[object]
$script:Secrets       = New-Object System.Collections.Generic.List[object]
$script:Procs         = New-Object System.Collections.Generic.List[object]
$script:Svcs          = New-Object System.Collections.Generic.List[object]
$script:Ports         = New-Object System.Collections.Generic.List[object]
$script:Tasks         = New-Object System.Collections.Generic.List[object]
$script:Containers    = New-Object System.Collections.Generic.List[object]
$script:Repos         = New-Object System.Collections.Generic.List[object]
# v1.1 : inventaire systeme (phase A) et decouverte des racines (phase B).
$script:Inventory     = New-Object System.Collections.Generic.List[object]
$script:Capabilities  = New-Object System.Collections.Generic.List[object]
$script:Hardware      = New-Object System.Collections.Generic.List[object]
$script:DiscoveryRoots = New-Object System.Collections.Generic.List[object]
$script:AllowedRoots  = New-Object System.Collections.Generic.List[string]
$script:AppDataTraversed = New-Object System.Collections.Generic.List[string]
$script:VersionsVerifiees = 0
$script:VersionsNonVerifiees = 0

$STATUT_OBSERVE = 'FAIT OBSERVE'
$STATUT_CANDIDAT = 'CANDIDAT'
$STATUT_NONVERIF = 'NON VERIFIE'
$ATTR_INCONNU = 'A DETERMINER'

# ---------------------------------------------------------------- utilitaires
function Test-Deadline {
    if ((Get-Date) -gt $script:Deadline) {
        if (-not $script:TimeBounded) {
            $script:TimeBounded = $true
            $script:ReportStatus = 'PARTIEL'
            $msg = 'Limite de temps atteinte (' + $MaxMinutes + ' minutes)'
            if (-not ($script:Limits -contains $msg)) { $script:Limits.Add($msg) }
            if (-not ($script:Ceilings -contains $msg)) { $script:Ceilings.Add($msg) }
            Write-Log -Message ('  ' + $msg) -Level 'AVERT'
        }
        return $false
    }
    return $true
}

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = ('{0} [{1}] {2}' -f (Get-Date).ToString('HH:mm:ss'), $Level, $Message)
    $script:Log.Add($line)
    Write-Host $line
    if ($script:JournalPath) {
        Add-Content -LiteralPath $script:JournalPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    }
}

function Hide-Sensitive {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
    $t = $Text
    # URL avec identifiants user:pass@
    $t = $t -replace '(?i)([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@', '$1***:***@'
    # URL avec jeton en position utilisateur (sans deux-points) - sur-masquage assume
    $t = $t -replace '(?i)([a-z][a-z0-9+.-]*://)[^/\s:@]+@', '$1***@'
    # options longues et courtes : --token, -p, -pw, -pass, --api-key...
    $t = $t -replace '(?i)(--?)(password|passwd|pass|pwd|pw|p|token|secret|apikey|api[-_]key|key|auth)([=:\s])\S+', '$1$2$3***'
    # affectations mot=valeur
    $t = $t -replace '(?i)(password|passwd|pwd|token|secret|apikey|api[-_]key|access_token|private_key)\s*[=:]\s*\S+', '$1=***'
    # Bearer avec ou sans espace, avec ou sans deux-points
    $t = $t -replace '(?i)(bearer)\s*:?\s*[A-Za-z0-9\-\._~+/=]{8,}', '$1 ***'
    # parametres d URL
    $t = $t -replace '(?i)([?&](key|token|apikey|api_key|access_token|sig|secret)=)[^&\s]+', '$1***'
    if ($t.Length -gt 160) { $t = $t.Substring(0, 160) + '...' }
    return $t
}

function Test-RootAllowed {
    param([string]$Path)
    $p = $Path.TrimEnd('\')
    # C10 : chemins UNC (reseau) refuses
    if ($p -match '^\\\\') { return @{ Ok = $false; Why = 'chemin UNC (reseau) interdit' } }
    if ($p -match '^[A-Za-z]:$') { return @{ Ok = $false; Why = 'racine de disque interdite' } }
    # C10 : lecteur non local refuse (Fixed uniquement)
    try {
        $root = [System.IO.Path]::GetPathRoot($p)
        if (-not $root) { return @{ Ok = $false; Why = 'lecteur non identifiable' } }
        $di = New-Object System.IO.DriveInfo($root)
        if ($di.DriveType -ne [System.IO.DriveType]::Fixed) {
            return @{ Ok = $false; Why = ('lecteur non local : ' + $di.DriveType) }
        }
    } catch {
        return @{ Ok = $false; Why = 'lecteur non identifiable' }
    }
    # C3 : la racine elle-meme ne doit pas etre un point de reanalyse
    $item = Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    if ($item -and (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
        return @{ Ok = $false; Why = 'la racine est une jonction ou un lien symbolique' }
    }
    # profils et dossiers personnels refuses comme racine
    $prof = $env:USERPROFILE.TrimEnd('\')
    $forbidden = @(
        $prof,
        (Join-Path $prof 'Desktop'),
        (Join-Path $prof 'Documents'),
        (Join-Path $prof 'Downloads'),
        (Join-Path $prof 'OneDrive')
    )
    foreach ($f in $forbidden) {
        if ($p -ieq $f.TrimEnd('\')) { return @{ Ok = $false; Why = 'profil ou repertoire personnel interdit comme racine' } }
    }
    return @{ Ok = $true; Why = '' }
}

# --------------------------------------------------- v1.1 : aides d inventaire
# Aucune commande de gestionnaire de paquets n est appelee (risque reseau).
# Seules des commandes de version explicitement listees sont autorisees, sur un
# executable identifie, sans interpreteur de commandes, avec delai maximal.

$script:VersionCommands = @{
    'python.exe'   = '--version'
    'python3.exe'  = '--version'
    'py.exe'       = '--version'
    'node.exe'     = '--version'
    'npm.cmd'      = '--version'
    'dotnet.exe'   = '--version'
    'java.exe'     = '-version'
    'javac.exe'    = '-version'
    'git.exe'      = '--version'
    'go.exe'       = 'version'
    'rustc.exe'    = '--version'
    'cargo.exe'    = '--version'
    'cmake.exe'    = '--version'
    'docker.exe'   = '--version'
    'podman.exe'   = '--version'
    'wsl.exe'      = '--version'
    'code.cmd'     = '--version'
    'nvidia-smi.exe' = '--version'
}

function Get-VersionSafe {
    param([string]$Exe, [int]$TimeoutSeconds = 5)
    $res = @{ Version = 'NON VERIFIEE'; Source = 'non determinee'; Ok = $false }
    if ([string]::IsNullOrWhiteSpace($Exe)) { return $res }
    $leaf = ''
    try { $leaf = [System.IO.Path]::GetFileName($Exe).ToLowerInvariant() } catch { return $res }
    if (-not $script:VersionCommands.ContainsKey($leaf)) { return $res }
    $arg = $script:VersionCommands[$leaf]
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Exe
        $psi.Arguments = $arg
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $proc = [System.Diagnostics.Process]::Start($psi)
        if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
            try { $proc.Kill() } catch { }
            return @{ Version = 'NON VERIFIEE'; Source = 'delai depasse (' + $TimeoutSeconds + ' s)'; Ok = $false }
        }
        $outTxt = ''
        try { $outTxt = $proc.StandardOutput.ReadToEnd() } catch { }
        try { $outTxt += ' ' + $proc.StandardError.ReadToEnd() } catch { }
        # Certains binaires (wsl.exe) renvoient de l UTF-16 : on retire les octets nuls
        # et les caracteres de controle avant toute journalisation.
        $outTxt = $outTxt -replace "`0", ''
        $outTxt = $outTxt -replace '[\x01-\x08\x0B\x0C\x0E-\x1F]', ' '
        $first = (($outTxt -split "`r?`n") | Where-Object { $_.Trim().Length -gt 0 } | Select-Object -First 1)
        if (-not $first) { $first = 'sortie vide' }
        $first = Hide-Sensitive ([string]$first).Trim()
        if ($first.Length -gt 120) { $first = $first.Substring(0, 120) }
        return @{ Version = $first; Source = 'commande de version autorisee'; Ok = $true }
    } catch {
        return @{ Version = 'NON VERIFIEE'; Source = 'execution impossible'; Ok = $false }
    }
}

function Add-Inventory {
    param([string]$Nom, [string]$Editeur, [string]$Version, [string]$Source, [string]$Statut = 'FAIT OBSERVE')
    if ($script:Inventory.Count -ge 3000) { Add-Limit -Message 'Logiciels inventories plafonnes a 3000' -Ceiling; return }
    $script:Inventory.Add([pscustomobject]@{
        nom = $Nom; editeur = $Editeur; version = $Version; source = $Source
        statut_verification = $Statut
    })
}

function Add-Capability {
    param([string]$Famille, [string]$Nom, [string]$Version, [string]$Chemin, [string]$Etat, [string]$Preuve)
    if ($script:Capabilities.Count -ge 2000) { Add-Limit -Message 'Capacites plafonnees a 2000' -Ceiling; return }
    $script:Capabilities.Add([pscustomobject]@{
        famille = $Famille; nom = $Nom; version = $Version; chemin = $Chemin
        etat = $Etat; preuve = $Preuve; statut_verification = $(if ($Version -eq 'NON VERIFIEE') { 'NON VERIFIE' } else { 'FAIT OBSERVE' })
    })
}

# ----------------------------------------------------- ajout d une ressource
function Add-Resource {
    param($File, [string]$Categorie)
    if ($script:Resources.Count -ge 5000) {
        Add-Limit -Message 'Ressources plafonnees a 5000' -Ceiling
        return
    }
    $script:Resources.Add([pscustomobject]@{
        id_temporaire = ('R' + ($script:Resources.Count + 1).ToString('00000'))
        nom = $File.Name
        chemin = $File.FullName
        taille_o = $File.Length
        date_modif = $File.LastWriteTime.ToString('yyyy-MM-dd HH:mm')
        extension = $File.Extension
        categorie = $Categorie
        systeme_appartenance = $ATTR_INCONNU
        projet = $ATTR_INCONNU
        systeme_responsable = $ATTR_INCONNU
        systemes_contributeurs = $ATTR_INCONNU
        provenance = $ATTR_INCONNU
        classification_proposee = $ATTR_INCONNU
        statut_verification = $STATUT_OBSERVE
        preuve = ('fichier present : ' + $Categorie)
    })
}

# ------------------------------------------------------ validation du perimetre
Write-Host ''
Write-Host '=== HORIZON PHASE 3 - AUDIT LECTURE SEULE ===' -ForegroundColor Cyan
Write-Host ''

if ($Roots.Count -gt 20) {
    throw ('-Roots : 20 chemins maximum (recu : ' + $Roots.Count + ').')
}
if ($Mode -eq 'Manuel' -and $Roots.Count -eq 0) {
    throw '-Mode Manuel exige au moins une racine dans -Roots.'
}

$validRoots = New-Object System.Collections.Generic.List[string]
foreach ($r in $Roots) {
    if (-not (Test-Path -LiteralPath $r -PathType Container)) {
        throw ('Racine introuvable : ' + $r)
    }
    $guard = Test-RootAllowed -Path $r
    if (-not $guard.Ok) {
        throw ('Racine refusee (' + $guard.Why + ') : ' + $r)
    }
    $full = (Resolve-Path -LiteralPath $r).Path
    if (-not $validRoots.Contains($full)) { $validRoots.Add($full) }
}

# ------------------------------------------------------------- dossier de sortie
if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}
$OutDir = (Resolve-Path -LiteralPath $OutDir).Path
$outNorm = $OutDir
try { $outNorm = [System.IO.Path]::GetFullPath($OutDir) } catch { }
foreach ($r in $validRoots) {
    $rn = $r
    try { $rn = [System.IO.Path]::GetFullPath($r) } catch { }
    $rn = $rn.TrimEnd('\') + '\'
    if ($outNorm.TrimEnd('\').StartsWith($rn, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'OutDir ne doit pas se trouver a l interieur d une racine auditee.'
    }
}

$fJournal  = Join-Path $OutDir '00_JOURNAL_AUDIT.log'
$fCand     = Join-Path $OutDir '01_SYSTEMES_CANDIDATS.csv'
$fRes      = Join-Path $OutDir '02_RESSOURCES.csv'
$fSynth    = Join-Path $OutDir '03_SYNTHESE.json'
$fInv      = Join-Path $OutDir '04_INVENTAIRE_SYSTEME.csv'
$fCap      = Join-Path $OutDir '05_CAPACITES.csv'

$script:JournalPath = $fJournal
Set-Content -LiteralPath $fJournal -Value ('# HORIZON PHASE 3 - journal - ' + (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) -Encoding UTF8

# C5 : tout le corps est protege ; les rapports sont ecrits dans le bloc finally.
try {

# ------------------------------------------------------------------- exclusions
$excludeSegments = @(
    'node_modules', '.venv', 'site-packages', '__pycache__',
    'Windows', 'Program Files', 'Program Files (x86)',
    'ProgramData', '$Recycle.Bin', 'System Volume Information',
    '.cache', '.npm-cache', 'Temp', 'Cache', 'CachedData',
    'Code Cache', 'GPUCache', 'Crashpad', 'logs'
)

# v1.1 : AppData n est plus exclu globalement. Il n est parcouru que dans les
# emplacements explicitement autorises (voir Initialize-AppDataAllowlist).
function Initialize-AppDataAllowlist {
    $cands = New-Object System.Collections.Generic.List[string]
    $local  = $env:LOCALAPPDATA
    $roam   = $env:APPDATA
    $prof   = $env:USERPROFILE
    if ($local)  { $cands.Add((Join-Path $local 'Programs')) }
    if ($prof) {
        foreach ($n in @('.ollama', '.cache', '.continue', '.cursor', '.claude', '.codex', '.gemini', '.config', '.lmstudio', '.lm-studio')) {
            $cands.Add((Join-Path $prof $n))
        }
    }
    if ($local) {
        foreach ($n in @('LM-Studio', 'LM Studio', 'Ollama', 'nomic.ai', 'AnthropicClaude', 'Programs\Microsoft VS Code')) {
            $cands.Add((Join-Path $local $n))
        }
    }
    if ($roam) {
        foreach ($n in @('Code', 'Cursor', 'Claude', 'Windsurf', 'LM Studio', 'Ollama')) {
            $cands.Add((Join-Path $roam $n))
        }
    }
    foreach ($c in $cands) {
        if (Test-Path -LiteralPath $c -PathType Container) {
            try {
                $full = [System.IO.Path]::GetFullPath($c)
                if (-not ($script:AllowedRoots -contains $full)) { $script:AllowedRoots.Add($full) }
            } catch { }
        }
    }
}

function Test-Excluded {
    param([string]$Full)
    if ([string]::IsNullOrWhiteSpace($Full)) { return $false }
    # v1.1 : un emplacement AppData explicitement autorise n est jamais exclu.
    $p = Get-FullPathNormalized $Full
    foreach ($a in $script:AllowedRoots) {
        $ap = (Get-FullPathNormalized $a).TrimEnd('\') + '\'
        if ($p.TrimEnd('\') -ieq $ap.TrimEnd('\')) { return $false }
        if ($p.StartsWith($ap, [StringComparison]::OrdinalIgnoreCase)) { return $false }
    }
    $parts = $p -split '[\\/]'
    foreach ($seg in $parts) {
        foreach ($x in $excludeSegments) {
            if ($seg -ieq $x) { return $true }
        }
    }
    return $false
}

function Get-FullPathNormalized {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return '' }
    try { return [System.IO.Path]::GetFullPath($Path) } catch { return $Path }
}

function Get-RootPrefix {
    param([string]$Root)
    $r = Get-FullPathNormalized $Root
    $sep = [string][System.IO.Path]::DirectorySeparatorChar
    if (-not $r.EndsWith($sep)) { $r = $r + $sep }
    return $r
}

function Test-PathInRoots {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    $p = Get-FullPathNormalized $Path
    if ([string]::IsNullOrWhiteSpace($p)) { return $false }
    foreach ($r in $validRoots) {
        $rn = (Get-FullPathNormalized $r).TrimEnd('\')
        if ($p.TrimEnd('\') -ieq $rn) { return $true }
        if ($p.StartsWith((Get-RootPrefix $r), [StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    return $false
}

# R6 : -Ceiling marque un plafond de collecte reellement atteint.
# Toute limite informative (Docker absent, points de reanalyse ignores) reste sans effet
# sur le statut ; tout plafond de collecte force PARTIEL et devient identifiable.
function Add-Limit {
    param([string]$Message, [switch]$Ceiling)
    if (-not ($script:Limits -contains $Message)) { $script:Limits.Add($Message) }
    if ($Ceiling) {
        $script:ReportStatus = 'PARTIEL'
        if (-not ($script:Ceilings -contains $Message)) { $script:Ceilings.Add($Message) }
    }
}

# C3 / C11 : parcours controle. Pas de recursion aveugle : points de reanalyse
# ignores, profondeur bornee, delai et volumetrie verifies a chaque element.
function Get-EntriesControlled {
    param([string]$Root, [string]$Mode = 'files')
    $stack = [System.Collections.Generic.Stack[object]]::new()
    $stack.Push([pscustomobject]@{ Path = $Root; Depth = 0 })
    $visited = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    while ($stack.Count -gt 0) {
        if (-not (Test-Deadline)) { Add-Limit -Message 'Limite de temps atteinte pendant le parcours' -Ceiling; return }
        $cur = $stack.Pop()
        if (-not $visited.Add($cur.Path)) { Add-Limit 'Boucle de repertoires evitee'; continue }
        if ($cur.Depth -gt 40) { Add-Limit -Message 'Profondeur maximale atteinte (40)' -Ceiling; continue }
        $entries = @(Get-ChildItem -LiteralPath $cur.Path -Force -ErrorAction SilentlyContinue)
        foreach ($e in $entries) {
            if (-not (Test-Deadline)) { Add-Limit -Message 'Limite de temps atteinte pendant le parcours' -Ceiling; return }
            # R6 : en mode 'dirs', aucun fichier n est compte par FilesSeen. Sans ce
            # compteur d entrees, le parcours n etait borne que par le temps.
            if ($Mode -eq 'dirs') {
                $script:EntriesSeen++
                if ($script:EntriesSeen -ge $MaxFiles) { Add-Limit -Message 'Limite d entrees atteinte (parcours)' -Ceiling; return }
            }
            $isReparse = (($e.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
            if ($isReparse) { Add-Limit 'Points de reanalyse ignores (jonctions, liens)'; continue }
            if ($e.PSIsContainer) {
                if (Test-Excluded $e.FullName) { continue }
                if ($Mode -eq 'dirs') { $e }
                $stack.Push([pscustomobject]@{ Path = $e.FullName; Depth = ($cur.Depth + 1) })
            } else {
                if ($Mode -ne 'files') { continue }
                if ($script:FilesSeen -ge $MaxFiles) { Add-Limit -Message 'Limite de fichiers atteinte' -Ceiling; return }
                $script:FilesSeen++
                $e
            }
        }
    }
}

# ============================== v1.1 PHASE B - DECOUVERTE DES RACINES TECHNIQUES
# Enumeration de niveau 1 uniquement : noms de repertoires et metadonnees.
# Aucune recursion, aucun contenu lu, aucune ecriture.

$techKeywords = @(
    'dev','develop','developpement','code','src','source','project','projet','repo','git',
    'ai','ia','llm','model','modeles','models','agent','agents','mcp','orchestr','hermes',
    'forge','game','jeu','studio','work','workspace','python','node','java','rust','dotnet',
    'docker','container','lab','sandbox','horizon','nzila','mayela','kof','gameforge','data'
)

function Test-TechName {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
    $n = $Name.ToLowerInvariant()
    foreach ($k in $techKeywords) { if ($n.Contains($k)) { return $true } }
    return $false
}

function Get-DiscoveryRoots {
    $found = New-Object System.Collections.Generic.List[object]
    $seen = New-Object System.Collections.Generic.HashSet[string]([StringComparer]::OrdinalIgnoreCase)
    $drives = @(Get-CimInstance Win32_LogicalDisk -ErrorAction SilentlyContinue | Where-Object { $_.DriveType -eq 3 })
    foreach ($d in $drives) {
        if (-not (Test-Deadline)) { break }
        $dr = $d.DeviceID + '\'
        $dirs = @(Get-ChildItem -LiteralPath $dr -Directory -Force -ErrorAction SilentlyContinue)
        foreach ($e in $dirs) {
            if (-not (Test-Deadline)) { break }
            if ((($e.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) { continue }
            if (Test-Excluded $e.FullName) { continue }
            if (-not (Test-TechName $e.Name)) { continue }
            if ($seen.Add($e.FullName)) {
                $found.Add([pscustomobject]@{ Chemin = $e.FullName; Motif = 'nom de repertoire porteur de mot-cle technique'; Niveau = 'racine de disque' })
            }
        }
    }
    $prof = $env:USERPROFILE
    if ($prof) {
        foreach ($base in @('Desktop','Documents','Downloads','OneDrive')) {
            $bp = Join-Path $prof $base
            if (-not (Test-Path -LiteralPath $bp -PathType Container)) { continue }
            $dirs = @(Get-ChildItem -LiteralPath $bp -Directory -Force -ErrorAction SilentlyContinue)
            foreach ($e in $dirs) {
                if (-not (Test-Deadline)) { break }
                if ((($e.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) { continue }
                if (Test-Excluded $e.FullName) { continue }
                if (-not (Test-TechName $e.Name)) { continue }
                if ($seen.Add($e.FullName)) {
                    $found.Add([pscustomobject]@{ Chemin = $e.FullName; Motif = 'sous-dossier de profil porteur de mot-cle technique'; Niveau = 'profil utilisateur' })
                }
            }
        }
    }
    return $found
}

# ---------------------------------------- application de la phase B (decouverte)
Initialize-AppDataAllowlist
if ($IncludeAppData) {
    Write-Log 'AppData cible : emplacements techniques autorises (lecture seule)'
    foreach ($a in $script:AllowedRoots) { Write-Log ('  - ' + $a) }
    if ($script:AllowedRoots.Count -eq 0) { Write-Log '  aucun emplacement AppData technique detecte' }
} else {
    Write-Log 'AppData non parcouru (switch -IncludeAppData absent)'
}

if ($validRoots.Count -eq 0) {
    Write-Log 'PHASE B - decouverte automatique des racines techniques (profondeur 1)'
    $disc = Get-DiscoveryRoots
    foreach ($c in $disc) {
        if (-not (Test-Deadline)) { break }
        if ($validRoots.Count -ge 20) { Add-Limit -Message 'Racines decouvertes plafonnees a 20' -Ceiling; break }
        if ($validRoots.Contains($c.Chemin)) { continue }
        $guard = Test-RootAllowed -Path $c.Chemin
        if (-not $guard.Ok) { Add-Limit -Message ('Racine candidate ignoree : ' + $c.Chemin + ' (' + $guard.Why + ')'); continue }
        $validRoots.Add($c.Chemin)
        $script:DiscoveryRoots.Add($c)
    }
    Write-Log ('  candidates examinees : ' + $disc.Count)
    Write-Log ('  racines retenues     : ' + $validRoots.Count)
    foreach ($r in $validRoots) { Write-Log ('    - ' + $r) }
}

# v1.1 : les emplacements AppData techniques autorises deviennent des racines
# de premiere classe lorsqu ils sont explicitement demandes.
if ($IncludeAppData) {
    foreach ($a in $script:AllowedRoots) {
        if ($validRoots.Count -ge 20) { Add-Limit -Message 'Racines plafonnees a 20 (AppData incluse)' -Ceiling; break }
        if ($validRoots.Contains($a)) { continue }
        $guard = Test-RootAllowed -Path $a
        if (-not $guard.Ok) { Add-Limit -Message ('Emplacement AppData ignore : ' + $a + ' (' + $guard.Why + ')'); continue }
        $validRoots.Add($a)
        $script:AppDataTraversed.Add($a)
        $script:DiscoveryRoots.Add([pscustomobject]@{ Chemin = $a; Motif = 'emplacement technique AppData autorise'; Niveau = 'appdata cible' })
    }
    Write-Log ('  racines AppData ajoutees : ' + $script:AppDataTraversed.Count)
}

# OutDir ne doit jamais se trouver dans une racine auditee (controle apres decouverte).
$outNorm2 = $OutDir
try { $outNorm2 = [System.IO.Path]::GetFullPath($OutDir) } catch { }
$rootsFinal = New-Object System.Collections.Generic.List[string]
foreach ($r in $validRoots) {
    $rn = $r
    try { $rn = [System.IO.Path]::GetFullPath($r) } catch { }
    $rn = $rn.TrimEnd('\') + '\'
    if ($outNorm2.TrimEnd('\').StartsWith($rn, [StringComparison]::OrdinalIgnoreCase)) {
        Write-Log -Message ('  racine ecartee car elle contient OutDir : ' + $r) -Level 'AVERT'
        Add-Limit ('Racine ecartee car elle contient OutDir : ' + $r)
        continue
    }
    if (-not ($rootsFinal.Contains($r))) { $rootsFinal.Add($r) }
}
$validRoots = $rootsFinal
if ($validRoots.Count -eq 0) {
    throw 'Aucune racine technique exploitable. Fournir -Roots avec -Mode Manuel.'
}

# ----------------------------------------------------- signatures (indices only)
$sigTokens = @(
    'orchestrator', 'orchestrateur', 'gameforge', 'forge-agent', 'forge_agent',
    'hermes', 'nzila', 'mayela',
    'langchain', 'langgraph', 'crewai', 'autogen', 'semantic-kernel',
    'llama-index', 'n8n', 'flowise', 'dify.ai', 'difyai', 'ollama',
    'lm-studio', 'lmstudio', 'comfyui', 'open-interpreter',
    'mcp-server', 'mcp.json', 'mcp-config'
) + $ExtraSignatures

$script:sigRegex = $null

function Initialize-Signatures {
    $alts = @()
    foreach ($t in $sigTokens) { $alts += [regex]::Escape([string]$t) }
    $pattern = '(?i)(?:^|[^a-z0-9])(?:' + ($alts -join '|') + ')(?:[^a-z0-9]|$)'
    $script:sigRegex = New-Object System.Text.RegularExpressions.Regex($pattern)
}

function Test-Signature {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
    if (-not $script:sigRegex) { Initialize-Signatures }
    return $script:sigRegex.IsMatch($Name)
}

$configPatterns = @(
    '*mcp*.json', 'claude_desktop_config.json', 'agents.json', 'agents.yaml',
    'AGENTS.md', 'orchestrator*', 'orchestrateur*', '*.agent.md', '.cursorrules',
    'settings.json', 'config.yaml', 'config.yml'
)
$configDirs = @('skills', 'prompts', 'agents', 'orchestrators', 'orchestrateurs', 'mcp')
$frameworkFiles = @('package.json', 'requirements.txt', 'pyproject.toml', 'Pipfile')
$frameworkKeys = @(
    'langchain', 'langgraph', 'crewai', 'autogen', 'semantic-kernel',
    'llama-index', 'n8n', 'flowise', 'dify', 'openai', 'anthropic', 'ollama'
)
$gamePatterns = @(
    '*.uproject', '*.uplugin', 'project.godot', '*.unity', 'Package.swift',
    '*.blend', '*.fbx', '*.uasset', '*.umap', '*.pak'
)
$dbPatterns = @('*.db', '*.sqlite', '*.sqlite3', '*.duckdb', '*.mdb', 'PGDATA', 'mongod.log')
$logPatterns = @('*.log')
$secretNames = @(
    '.env', '.env.local', '.env.production', '.npmrc', '.netrc',
    'credentials', 'credentials.json', 'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    '*.pem', '*.key', '*.pfx', '*.p12', '*.keystore', 'secrets.json'
)

# ------------------------------------------------------------- M0 - identite du run
$scriptHash = 'indisponible'
if ($PSCommandPath -and (Test-Path -LiteralPath $PSCommandPath)) {
    $scriptHash = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
}
Write-Log 'M0 - identite du run'
Write-Log ('  poste            : ' + $env:COMPUTERNAME)
Write-Log ('  utilisateur      : ' + $env:USERNAME)
Write-Log ('  systeme          : ' + [System.Environment]::OSVersion.VersionString)
Write-Log ('  date de debut    : ' + $script:StartedAt.ToString('yyyy-MM-dd HH:mm:ss'))
Write-Log ('  version script   : ' + $script:ScriptVersion)
Write-Log ('  empreinte script : ' + $scriptHash)
Write-Log ('  limite de temps  : ' + $MaxMinutes + ' minutes')
Write-Log ('  limite fichiers  : ' + $MaxFiles)
Write-Log ('  racines autorisees (' + $validRoots.Count + ') :')
foreach ($r in $validRoots) { Write-Log ('    - ' + $r) }
Write-Log ('  dossier de sortie : ' + $OutDir)
Write-Log ('  mode             : ' + $Mode)
Write-Log ('  appdata cible    : ' + $(if ($IncludeAppData) { 'oui' } else { 'non' }))

# ================================================== v1.1 PHASE A - INVENTAIRE
# ------------------------------------------------ M12 - materiel, OS, stockage
Write-Log 'M12 - materiel, systeme d exploitation, stockage (WMI, lecture seule)'

$cs = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
$osObj = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
$cpuList = @(Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue)
$memList = @(Get-CimInstance Win32_PhysicalMemory -ErrorAction SilentlyContinue)
$gpuList = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue)
$diskList = @(Get-CimInstance Win32_DiskDrive -ErrorAction SilentlyContinue)
$logicalList = @(Get-CimInstance Win32_LogicalDisk -ErrorAction SilentlyContinue | Where-Object { $_.DriveType -eq 3 })

if ($cs) {
    $script:Hardware.Add([pscustomobject]@{
        element = 'Machine'; valeur = [string]$cs.Name
        detail = ('fabricant=' + $cs.Manufacturer + ' ; modele=' + $cs.Model + ' ; domaine=' + $cs.Domain + ' ; virtualisation=' + $cs.HypervisorPresent)
        source = 'Win32_ComputerSystem'
    })
}
if ($osObj) {
    $uptime = 'inconnu'
    try { $uptime = [string]([math]::Round(((Get-Date) - $osObj.LastBootUpTime).TotalHours, 2)) + ' h' } catch { }
    $script:Hardware.Add([pscustomobject]@{
        element = 'Systeme'; valeur = [string]$osObj.Caption
        detail = ('version=' + $osObj.Version + ' ; build=' + $osObj.BuildNumber + ' ; arch=' + $osObj.OSArchitecture + ' ; uptime=' + $uptime)
        source = 'Win32_OperatingSystem'
    })
}
foreach ($c in $cpuList) {
    $script:Hardware.Add([pscustomobject]@{
        element = 'CPU'; valeur = [string]$c.Name
        detail = ('coeurs=' + $c.NumberOfCores + ' ; logiques=' + $c.NumberOfLogicalProcessors + ' ; frequence_MHz=' + $c.MaxClockSpeed)
        source = 'Win32_Processor'
    })
}
$ramTotal = 0
try { $ramTotal = [math]::Round((($memList | Measure-Object -Property Capacity -Sum).Sum) / 1GB, 2) } catch { }
$script:Hardware.Add([pscustomobject]@{
    element = 'RAM'; valeur = ([string]$ramTotal + ' Go')
    detail = ('barrettes=' + $memList.Count)
    source = 'Win32_PhysicalMemory'
})
foreach ($g in $gpuList) {
    $vram = ''
    if ($g.AdapterRAM -and $g.AdapterRAM -gt 0) { $vram = [string]([math]::Round($g.AdapterRAM / 1GB, 2)) + ' Go' }
    $script:Hardware.Add([pscustomobject]@{
        element = 'GPU'; valeur = [string]$g.Name
        detail = ('VRAM=' + $vram + ' ; pilote=' + $g.DriverVersion)
        source = 'Win32_VideoController'
    })
}
foreach ($dsk in $diskList) {
    $script:Hardware.Add([pscustomobject]@{
        element = 'Disque physique'; valeur = [string]$dsk.Model
        detail = ('taille=' + [math]::Round($dsk.Size / 1GB, 2) + ' Go ; interface=' + $dsk.InterfaceType)
        source = 'Win32_DiskDrive'
    })
}
foreach ($lv in $logicalList) {
    $pct = ''
    if ($lv.Size -gt 0) { $pct = [string]([math]::Round(100 * $lv.FreeSpace / $lv.Size, 1)) + ' %' }
    $script:Hardware.Add([pscustomobject]@{
        element = 'Volume'; valeur = [string]$lv.DeviceID
        detail = ('taille=' + [math]::Round($lv.Size / 1GB, 2) + ' Go ; libre=' + [math]::Round($lv.FreeSpace / 1GB, 2) + ' Go (' + $pct + ')')
        source = 'Win32_LogicalDisk'
    })
}
Write-Log ('  elements materiels releves : ' + $script:Hardware.Count)

# ---------------------------------------------------- M13 - logiciels installes
Write-Log 'M13 - logiciels installes (registre Uninstall, lecture seule)'
$uninstallKeys = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$seenSoftware = New-Object System.Collections.Generic.HashSet[string]([StringComparer]::OrdinalIgnoreCase)
foreach ($k in $uninstallKeys) {
    if (-not (Test-Deadline)) { break }
    $entries = @(Get-ItemProperty -Path $k -ErrorAction SilentlyContinue)
    foreach ($e in $entries) {
        if (-not $e.DisplayName) { continue }
        $nom = [string]$e.DisplayName
        $ver = [string]$e.DisplayVersion
        $id = ($nom + '|' + $ver).ToLowerInvariant()
        if (-not ($seenSoftware.Add($id))) { continue }
        Add-Inventory $nom ([string]$e.Publisher) $ver 'registre Uninstall'
    }
}
Write-Log ('  logiciels inventories : ' + $script:Inventory.Count)

# ------------------------------------- M14 - langages, SDK, runtimes, compilateurs
Write-Log 'M14 - langages, SDK, runtimes, compilateurs (commandes de version autorisees)'
$toolList = @(
    'python.exe','python3.exe','py.exe','node.exe','npm.cmd','dotnet.exe',
    'java.exe','javac.exe','git.exe','go.exe','rustc.exe','cargo.exe',
    'cmake.exe','code.cmd','nvidia-smi.exe','docker.exe','podman.exe','wsl.exe'
)
foreach ($t in $toolList) {
    if (-not (Test-Deadline)) { break }
    $c = Get-Command $t -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $c) { continue }
    $exe = [string]$c.Source
    if (-not $exe) { $exe = [string]$c.Path }
    $v = Get-VersionSafe -Exe $exe -TimeoutSeconds $VersionTimeoutSeconds
    if ($v.Ok) { $script:VersionsVerifiees++ } else { $script:VersionsNonVerifiees++ }
    Add-Capability 'runtime' $t $v.Version $exe $v.Source 'executable present dans le PATH'
    Write-Log ('  ' + $t + ' : ' + $v.Version + ' (' + $v.Source + ')')
}
foreach ($ev in @('JAVA_HOME','DOTNET_ROOT','CUDA_PATH','CONDA_PREFIX','NODE_PATH','GOROOT','RUSTUP_HOME','CARGO_HOME')) {
    $val = [Environment]::GetEnvironmentVariable($ev)
    if ($val) { Add-Capability 'variable environnement' $ev 'NON VERIFIEE' $val 'declaree' 'variable de processus ou machine' }
}
Write-Log ('  capacites relevees : ' + $script:Capabilities.Count)

# ------------------------------------- M15 - outils IA, frameworks et modeles locaux
Write-Log 'M15 - outils IA et modeles locaux (noms, extensions, tailles ; contenu jamais lu)'
foreach ($t in @('ollama.exe','lm-studio.exe','comfyui.exe','nomic.exe','open-interpreter.exe')) {
    $c = Get-Command $t -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { Add-Capability 'outil IA' $t 'NON VERIFIEE' ([string]$c.Source) 'executable detecte' 'presence dans le PATH' }
}
$modelDirs = New-Object System.Collections.Generic.List[string]
if ($env:USERPROFILE) {
    foreach ($n in @('.ollama\models', '.cache\lm-studio', '.cache\huggingface', '.lmstudio\models', '.lm-studio\models')) { $modelDirs.Add((Join-Path $env:USERPROFILE $n)) }
}
if ($env:LOCALAPPDATA) {
    foreach ($n in @('LM-Studio', 'LM Studio', 'Ollama', 'nomic.ai')) { $modelDirs.Add((Join-Path $env:LOCALAPPDATA $n)) }
}
$modelExt = @('.gguf','.safetensors','.onnx','.pt','.pth','.ckpt','.bin')
$modelCount = 0
$modelBytes = 0
foreach ($md in $modelDirs) {
    if (-not (Test-Path -LiteralPath $md -PathType Container)) { continue }
    Add-Capability 'emplacement modeles' (Split-Path $md -Leaf) 'NON VERIFIEE' $md 'repertoire present' 'presence de repertoire'
    foreach ($f in @(Get-ChildItem -LiteralPath $md -File -Recurse -Force -ErrorAction SilentlyContinue)) {
        if (-not (Test-Deadline)) { break }
        if ($modelExt -contains $f.Extension.ToLowerInvariant()) {
            $modelCount++
            $modelBytes += $f.Length
            Add-Resource $f 'modele local (non lu)'
        }
    }
}
Write-Log ('  fichiers de modeles locaux : ' + $modelCount + ' (' + [math]::Round($modelBytes / 1GB, 2) + ' Go)')

# ------------------------------------- M16 - agents, orchestrateurs, configurations MCP
Write-Log 'M16 - configurations agents/MCP dans les emplacements autorises'
$agentConfigNames = @('*mcp*.json','claude_desktop_config.json','agents.json','agents.yaml','AGENTS.md','orchestrator*','orchestrateur*','*.agent.md','.cursorrules')
$agentCount = 0
$agentRoots = New-Object System.Collections.Generic.List[string]
if ($env:USERPROFILE) { $agentRoots.Add($env:USERPROFILE) }
foreach ($a in $script:AllowedRoots) { $agentRoots.Add($a) }
foreach ($ar in $agentRoots) {
    if (-not (Test-Path -LiteralPath $ar -PathType Container)) { continue }
    foreach ($pat in $agentConfigNames) {
        foreach ($f in @(Get-ChildItem -LiteralPath $ar -Filter $pat -File -Force -ErrorAction SilentlyContinue)) {
            if (-not (Test-Deadline)) { break }
            $agentCount++
            Add-Capability 'configuration agent/MCP' $f.Name 'NON VERIFIEE' $f.FullName 'fichier present' 'presence de configuration'
            Add-Resource $f 'configuration'
        }
    }
}
Write-Log ('  configurations agents/MCP reperees : ' + $agentCount)

# ------------------------------------- garde-fou : refus d un perimetre trop large
# C11 : la volumetrie n est plus comptee par une passe recursive separee.
# Le plafond est applique pendant le parcours controle (Get-EntriesControlled).
Write-Log ('  volumetrie : comptee pendant le parcours controle, plafond ' + $MaxFiles + ' fichiers')

# ------------------------------------------- M1 - processus, services et ports
Write-Log 'M1 - processus, services, ports (filtres)'

$procList = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
foreach ($p in $procList) {
    if (-not (Test-Deadline)) { break }
    $exe = $p.ExecutablePath
    $keep = (Test-PathInRoots $exe) -or (Test-Signature $p.Name)
    if (-not $keep) { continue }
    $hasArgs = 'non'
    if ($p.CommandLine -and ($p.CommandLine.Trim().Length -gt ($p.Name.Length + 1))) { $hasArgs = 'oui' }
    $script:Procs.Add([pscustomobject]@{
        Nom = $p.Name
        PID = $p.ProcessId
        Chemin = $exe
        ArgumentsPresents = $hasArgs
    })
    if ($script:Procs.Count -ge 300) { Add-Limit -Message 'Processus retenus plafonnes a 300' -Ceiling; break }
}
Write-Log ('  processus retenus : ' + $script:Procs.Count)

$svcList = Get-CimInstance Win32_Service -ErrorAction SilentlyContinue
foreach ($s in $svcList) {
    if (-not (Test-Deadline)) { break }
    $keep = (Test-PathInRoots $s.PathName) -or (Test-Signature $s.Name) -or (Test-Signature $s.DisplayName)
    if (-not $keep) { continue }
    $script:Svcs.Add([pscustomobject]@{
        Nom = $s.Name
        Etat = $s.State
        Chemin = (Hide-Sensitive $s.PathName)
    })
    if ($script:Svcs.Count -ge 100) { Add-Limit -Message 'Services retenus plafonnes a 100' -Ceiling; break }
}
Write-Log ('  services retenus  : ' + $script:Svcs.Count)

$retainedPids = @($script:Procs | ForEach-Object { $_.PID })
if ($retainedPids.Count -gt 0) {
    $conns = @()
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) { $conns = @(Get-NetTCPConnection -State Listen) }
    foreach ($c in $conns) {
        if ($retainedPids -contains $c.OwningProcess) {
            $pr = $script:Procs | Where-Object { $_.PID -eq $c.OwningProcess } | Select-Object -First 1
            $script:Ports.Add([pscustomobject]@{
                Port = $c.LocalPort
                Adresse = $c.LocalAddress
                PID = $c.OwningProcess
                Processus = $(if ($pr) { $pr.Nom } else { '' })
            })
        }
    }
}
Write-Log ('  ports en ecoute   : ' + $script:Ports.Count + ' (uniquement ceux des processus retenus)')

# --------------------------------------------------- M2 - conteneurs et WSL
Write-Log 'M2 - conteneurs et WSL (si presents)'

# C4 : aucun endpoint distant. Verification systematique avant tout appel.
function Test-ContainerEndpointLocal {
    param([string]$Tool)
    if ($Tool -eq 'docker') {
        $h = $env:DOCKER_HOST
        if ($h -and ($h -notmatch '(?i)^(npipe:|unix:|fd:)')) {
            return @{ Ok = $false; Why = ('DOCKER_HOST non local : ' + (Hide-Sensitive $h)) }
        }
        $c = $env:DOCKER_CONTEXT
        if ($c -and ($c -notmatch '(?i)^(default|desktop-linux)$')) {
            return @{ Ok = $false; Why = ('DOCKER_CONTEXT declare : ' + $c) }
        }
        # R2 : aucune commande docker executee. Lecture du seul champ currentContext.
        $cfg = Join-Path $env:USERPROFILE '.docker\config.json'
        if (Test-Path -LiteralPath $cfg) {
            $raw = Get-Content -LiteralPath $cfg -Raw -ErrorAction SilentlyContinue
            if ($raw) {
                $m = [regex]::Match([string]$raw, '"currentContext"\s*:\s*"([^"]+)"')
                if ($m.Success) {
                    $actx = $m.Groups[1].Value
                    $script:ContainerEnv = ('currentContext declare : ' + $actx)
                    if ($actx -and ($actx -notmatch '(?i)^(default|desktop-linux)$')) {
                        return @{ Ok = $false; Why = ('contexte docker declare non local : ' + $actx) }
                    }
                } else {
                    $script:ContainerEnv = 'config.json present, aucun currentContext'
                }
            }
            $raw = $null
        } else {
            $script:ContainerEnv = 'aucun fichier ~/.docker/config.json'
        }
    }
    if ($Tool -eq 'podman') {
        $h = $env:CONTAINER_HOST
        if ($h -and ($h -notmatch '(?i)^(npipe:|unix:)')) {
            return @{ Ok = $false; Why = ('CONTAINER_HOST non local : ' + (Hide-Sensitive $h)) }
        }
    }
    return @{ Ok = $true; Why = '' }
}

# v1.1 : inventaire lecture seule autorise UNIQUEMENT sur endpoint local confirme.
# Aucune modification de contexte, aucun demarrage/arret/suppression de conteneur.
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $chk = Test-ContainerEndpointLocal 'docker'
    if (-not $chk.Ok) {
        Write-Log -Message ('  docker ignore : ' + $chk.Why) -Level 'AVERT'
        Add-Limit ('Docker : ' + $chk.Why)
        Add-Capability 'conteneur' 'docker' 'NON VERIFIEE' '' 'endpoint distant ou indetermine' 'presence detectee'
    } elseif ($AllowContainerInventory) {
        $dv = Get-VersionSafe -Exe 'docker.exe' -TimeoutSeconds $VersionTimeoutSeconds
        Add-Capability 'conteneur' 'docker' $dv.Version 'docker.exe' $dv.Source 'endpoint local confirme'
        if ($dv.Ok) { $script:VersionsVerifiees++ } else { $script:VersionsNonVerifiees++ }
        $psOut = @(& docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}' 2>$null)
        foreach ($l in $psOut) {
            if (-not $l) { continue }
            $parts = ([string]$l) -split '\|'
            $script:Containers.Add([pscustomobject]@{
                Type = 'docker'; Nom = $(if ($parts.Count -gt 0) { $parts[0] } else { '' })
                Image = $(if ($parts.Count -gt 1) { $parts[1] } else { '' })
                Etat = $(if ($parts.Count -gt 2) { $parts[2] } else { '' })
            })
        }
        Write-Log ('  conteneurs docker en cours : ' + @($psOut).Count)
    } else {
        Write-Log '  conteneurs docker : inventaire non execute (switch -AllowContainerInventory absent)'
        Add-Limit 'Inventaire Docker non execute (switch -AllowContainerInventory absent)'
        Add-Capability 'conteneur' 'docker' 'NON VERIFIEE' '' 'inventaire non autorise' 'presence detectee'
    }
} else {
    Add-Limit 'Docker absent de ce poste'
}

if (Get-Command podman -ErrorAction SilentlyContinue) {
    $chk = Test-ContainerEndpointLocal 'podman'
    if (-not $chk.Ok) {
        Write-Log -Message ('  podman ignore : ' + $chk.Why) -Level 'AVERT'
        Add-Limit ('Podman : ' + $chk.Why)
        Add-Capability 'conteneur' 'podman' 'NON VERIFIEE' '' 'endpoint distant ou indetermine' 'presence detectee'
    } elseif ($AllowContainerInventory) {
        $pv = Get-VersionSafe -Exe 'podman.exe' -TimeoutSeconds $VersionTimeoutSeconds
        Add-Capability 'conteneur' 'podman' $pv.Version 'podman.exe' $pv.Source 'endpoint local confirme'
        $psOut = @(& podman ps --format '{{.Names}}|{{.Image}}|{{.Status}}' 2>$null)
        foreach ($l in $psOut) {
            if (-not $l) { continue }
            $parts = ([string]$l) -split '\|'
            $script:Containers.Add([pscustomobject]@{
                Type = 'podman'; Nom = $(if ($parts.Count -gt 0) { $parts[0] } else { '' })
                Image = $(if ($parts.Count -gt 1) { $parts[1] } else { '' })
                Etat = $(if ($parts.Count -gt 2) { $parts[2] } else { '' })
            })
        }
    } else {
        Write-Log '  conteneurs podman : inventaire non execute (switch -AllowContainerInventory absent)'
        Add-Limit 'Inventaire Podman non execute (switch -AllowContainerInventory absent)'
        Add-Capability 'conteneur' 'podman' 'NON VERIFIEE' '' 'inventaire non autorise' 'presence detectee'
    }
}
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    foreach ($l in (& wsl -l -v 2>$null)) {
        $t = ($l -replace "`0", '').Trim()
        if ($t -and $t -notmatch '^(NAME|NOM)') {
            $script:Containers.Add([pscustomobject]@{ Type = 'wsl'; Nom = $t; Image = '' })
        }
    }
}
Write-Log ('  conteneurs / wsl  : ' + $script:Containers.Count)

# ---------------------------------------------- M3 - taches planifiees pertinentes
Write-Log 'M3 - taches planifiees pointant dans le perimetre'
$schedTasks = @()
if (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue) { $schedTasks = @(Get-ScheduledTask) }
foreach ($t in $schedTasks) {
    if (-not (Test-Deadline)) { break }
    $actions = $t.Actions
    foreach ($a in $actions) {
        $ex = ''
        if ($a.Execute) { $ex = $a.Execute }
        $arg = ''
        if ($a.Arguments) { $arg = $a.Arguments }
        if ((Test-PathInRoots $ex) -or (Test-Signature $t.TaskName) -or (Test-Signature $ex)) {
            $script:Tasks.Add([pscustomobject]@{
                Nom = $t.TaskName
                Chemin = (Hide-Sensitive $ex)
                Arguments = (Hide-Sensitive $arg)
                Etat = [string]$t.State
            })
            break
        }
    }
    if ($script:Tasks.Count -ge 60) { Add-Limit -Message 'Taches planifiees plafonnees a 60' -Ceiling; break }
}
Write-Log ('  taches retenues   : ' + $script:Tasks.Count)

# ------------------------------------------ M5a - reperage des depots (.git)
Write-Log 'M5a - reperage des depots Git dans le perimetre'
$gitRoots = New-Object System.Collections.Generic.List[string]
$gitAvailable = [bool](Get-Command git -ErrorAction SilentlyContinue)
foreach ($r in $validRoots) {
    if (-not (Test-Deadline)) { break }
    Get-EntriesControlled -Root $r -Mode 'dirs' | Where-Object { $_.Name -eq '.git' } | ForEach-Object {
        if ($script:ReposBounded) { return }
        $g = $_
        if (Test-Excluded $g.FullName) { return }
        $root = $g.Parent.FullName
        if ($gitRoots.Count -ge 100) {
            Add-Limit -Message 'Depots plafonnes a 100' -Ceiling
            $script:ReposBounded = $true
            return
        }
        if (-not ($gitRoots.Contains($root))) { $gitRoots.Add($root) }
    }
    if ($script:ReposBounded) { break }
}
Write-Log ('  depots detectes   : ' + $gitRoots.Count)

foreach ($gr in $gitRoots) {
    $remote = ''
    $branch = ''
    $commit = ''
    if ($gitAvailable) {
        $rv = & git -C $gr remote -v 2>$null | Select-Object -First 1
        if ($rv) { $remote = Hide-Sensitive ([string]$rv) }
        $br = & git -C $gr rev-parse --abbrev-ref HEAD 2>$null
        if ($br) { $branch = ([string]$br).Trim() }
        $lg = & git -C $gr log -1 --format='%H|%cI' 2>$null
        if ($lg) { $commit = ([string]$lg).Trim() }
    }
    $script:Repos.Add([pscustomobject]@{
        Chemin = $gr
        RemoteMasque = $remote
        Branche = $branch
        DernierCommit = $commit
    })
    $script:Evidence.Add([pscustomobject]@{
        Candidat = $gr
        Type = 'depot Git'
        Chemin = $gr
        Detail = ('branche=' + $branch)
        Statut = $STATUT_OBSERVE
    })
}
Write-Log ('  depots renseignes : ' + $script:Repos.Count)

# ------------------------------------------- rattachement d un fichier a un candidat
function Get-CandidateKey {
    param([string]$FullPath)
    $p = Get-FullPathNormalized $FullPath
    foreach ($gr in $gitRoots) {
        $gpref = Get-RootPrefix $gr
        if ($p.StartsWith($gpref, [StringComparison]::OrdinalIgnoreCase)) { return $gr }
    }
    foreach ($r in $validRoots) {
        $pref = Get-RootPrefix $r
        if ($p.StartsWith($pref, [StringComparison]::OrdinalIgnoreCase)) {
            $rest = $p.Substring($pref.Length)
            $seg = ($rest -split '\\')[0]
            if ($seg -and $rest.Contains('\')) { return (Join-Path $r $seg) }
            return $r
        }
    }
    return $FullPath
}

# --------------------------------- M4/M6/M7/M8 - analyse des fichiers du perimetre
Write-Log 'M4/M6/M7/M8 - analyse des fichiers (configurations, moteurs, bases, journaux, secrets)'
if (-not $DiscoveryOnly) {
foreach ($r in $validRoots) {
    if (-not (Test-Deadline)) { break }
    Write-Log ('  analyse : ' + $r)
    Get-EntriesControlled -Root $r -Mode 'files' | ForEach-Object {
        $f = $_
        if (Test-Excluded $f.FullName) { return }

        $name = $f.Name
        $lower = $name.ToLowerInvariant()
        $key = Get-CandidateKey -FullPath $f.FullName

        $isConfig = $false
        foreach ($pat in $configPatterns) { if ($name -like $pat) { $isConfig = $true; break } }
        $isGame = $false
        foreach ($pat in $gamePatterns) { if ($name -like $pat) { $isGame = $true; break } }
        $isDb = $false
        foreach ($pat in $dbPatterns) { if ($name -like $pat) { $isDb = $true; break } }
        $isFramework = ($frameworkFiles -contains $lower)

        $isSecret = ($name -like '.env*')
        if (-not $isSecret) {
            foreach ($pat in $secretNames) { if ($name -like $pat) { $isSecret = $true; break } }
        }
        $byName = Test-Signature $name

        # secrets : presence seulement, contenu JAMAIS lu
        if ($isSecret) {
            $script:Secrets.Add([pscustomobject]@{
                Nom = $name; Chemin = $f.FullName; Taille = $f.Length
                DateModif = $f.LastWriteTime.ToString('yyyy-MM-dd HH:mm'); Present = 'oui'
            })
            $script:Evidence.Add([pscustomobject]@{
                Candidat = $key; Type = 'fichier de secrets (non lu)'; Chemin = $f.FullName
                Detail = ('taille=' + $f.Length + ' o'); Statut = $STATUT_OBSERVE
            })
            continue
        }

        if ($isConfig) {
            $script:Evidence.Add([pscustomobject]@{
                Candidat = $key; Type = 'configuration agent/MCP'; Chemin = $f.FullName
                Detail = ('motif=' + $name); Statut = $STATUT_CANDIDAT
            })
            Add-Resource $f 'configuration'
        }

        if ($isFramework -and $f.Length -lt 300000) {
            $txt = Get-Content -LiteralPath $f.FullName -Raw -ErrorAction SilentlyContinue
            if ($txt) {
                $low = $txt.ToLowerInvariant()
                $hits = New-Object System.Collections.Generic.List[string]
                foreach ($k in $frameworkKeys) { if ($low.Contains($k)) { $hits.Add($k) } }
                if ($hits.Count -gt 0) {
                    $script:Evidence.Add([pscustomobject]@{
                        Candidat = $key; Type = 'framework d agents'; Chemin = $f.FullName
                        Detail = ('indices=' + ($hits -join ',')); Statut = $STATUT_CANDIDAT
                    })
                }
            }
        }

        if ($isGame) {
            $script:Evidence.Add([pscustomobject]@{
                Candidat = $key; Type = 'artefact de projet de jeu'; Chemin = $f.FullName
                Detail = ('motif=' + $name); Statut = $STATUT_CANDIDAT
            })
            Add-Resource $f 'projet de jeu'
        }

        if ($isDb) {
            $script:Evidence.Add([pscustomobject]@{
                Candidat = $key; Type = 'base de donnees locale'; Chemin = $f.FullName
                Detail = ('taille=' + $f.Length + ' o'); Statut = $STATUT_OBSERVE
            })
            Add-Resource $f 'base locale'
        }

        if ($byName -and -not $isConfig -and -not $isGame) {
            $script:Evidence.Add([pscustomobject]@{
                Candidat = $key; Type = 'nom porteur de signature'; Chemin = $f.FullName
                Detail = $name; Statut = $STATUT_CANDIDAT
            })
        }
    }
}
}
Write-Log ('  fichiers parcourus : ' + $script:FilesSeen)
Write-Log ('  indices collectes  : ' + $script:Evidence.Count)
Write-Log ('  fichiers de secrets detectes (non lus) : ' + $script:Secrets.Count)

} catch {
    $script:ReportStatus = 'PARTIEL'
    $msgErr = [string]$_.Exception.Message
    if (-not ($script:Errors -contains $msgErr)) { $script:Errors.Add($msgErr) }
    Write-Log -Message ('ERREUR : ' + $msgErr) -Level 'ERREUR'
    Add-Content -LiteralPath $fJournal -Value ('# ERREUR INTERCEPTEE : ' + $msgErr) -Encoding UTF8 -ErrorAction SilentlyContinue
} finally {
    # C5 : tout ce qui suit s execute meme si le corps a echoue (rapport partiel).

# ------------------------------------------- M9/M10 - agregation et restitution
Write-Log 'M9/M10 - agregation des indices par candidat'

if (-not $script:Evidence) { $script:Evidence = New-Object System.Collections.Generic.List[object] }
$candidats = New-Object System.Collections.Generic.List[object]
$grouped = $script:Evidence | Group-Object -Property Candidat
$idx = 0
foreach ($g in $grouped) {
    $idx++
    $types = @($g.Group | ForEach-Object { $_.Type } | Sort-Object -Unique)
    $nbObs = @($g.Group | Where-Object { $_.Statut -eq $STATUT_OBSERVE }).Count
    $nbCand = @($g.Group | Where-Object { $_.Statut -eq $STATUT_CANDIDAT }).Count
    $candidats.Add([pscustomobject]@{
        id_candidat = ('C' + $idx.ToString('000'))
        chemin_candidat = $g.Name
        nom_propose = (Split-Path $g.Name -Leaf)
        types_d_indices = ($types -join ' ; ')
        preuves_observees = $nbObs
        indices_a_confirmer = $nbCand
        total_indices = $g.Count
        processus_associes = (@($script:Procs | Where-Object { Test-Signature $_.Nom } | ForEach-Object { $_.Nom } | Sort-Object -Unique) -join ',')
        ports_associes = (@($script:Ports | ForEach-Object { [string]$_.Port } | Sort-Object -Unique) -join ',')
        service_associe = (@($script:Svcs | Where-Object { Test-Signature $_.Nom } | ForEach-Object { $_.Nom } | Sort-Object -Unique) -join ',')
        statut = $STATUT_CANDIDAT
        qualification = 'NON QUALIFIE - decision humaine requise'
        justification = ('faisceau de ' + $g.Count + ' indice(s) ; aucune attribution automatique')
    })
}
foreach ($r in $validRoots) {
    $has = @($script:Evidence | Where-Object { $_.Candidat -like ($r + '*') }).Count
    if ($has -eq 0) {
        $candidats.Add([pscustomobject]@{
            id_candidat = ('C' + ($idx + 1).ToString('000')); chemin_candidat = $r
            nom_propose = (Split-Path $r -Leaf); types_d_indices = ''
            preuves_observees = 0; indices_a_confirmer = 0; total_indices = 0
            processus_associes = ''; ports_associes = ''; service_associe = ''
            statut = $STATUT_NONVERIF
            qualification = 'NON QUALIFIE - decision humaine requise'
            justification = 'aucun indice detecte dans les fichiers parcourus de cette racine'
        })
        $idx++
    }
}
Write-Log ('  candidats constitues : ' + $candidats.Count)

# C8 : neutralisation de l injection de formules dans les exports CSV
function Protect-Object {
    param($Item)
    if ($null -eq $Item) { return $Item }
    foreach ($pr in $Item.PSObject.Properties) {
        if ($pr.Value -is [string] -and $pr.Value -match '^[=+\-@]') {
            $pr.Value = "'" + $pr.Value
        }
    }
    return $Item
}

# ---------------------------------------------------------------- ecriture des sorties
if ($candidats -and $candidats.Count -gt 0) {
    $candidats | ForEach-Object { Protect-Object $_ } | Export-Csv -LiteralPath $fCand -NoTypeInformation -Encoding UTF8
} else {
    Set-Content -LiteralPath $fCand -Value 'id_candidat,chemin_candidat' -Encoding UTF8
}
if ($script:Resources -and $script:Resources.Count -gt 0) {
    $script:Resources | ForEach-Object { Protect-Object $_ } | Export-Csv -LiteralPath $fRes -NoTypeInformation -Encoding UTF8
} else {
    Set-Content -LiteralPath $fRes -Value 'id_temporaire,chemin' -Encoding UTF8
}
# v1.1 : inventaire systeme et capacites techniques
if ($script:Inventory -and $script:Inventory.Count -gt 0) {
    $script:Inventory | ForEach-Object { Protect-Object $_ } | Export-Csv -LiteralPath $fInv -NoTypeInformation -Encoding UTF8
} else {
    Set-Content -LiteralPath $fInv -Value 'nom,editeur,version,source,statut_verification' -Encoding UTF8
}
if ($script:Capabilities -and $script:Capabilities.Count -gt 0) {
    $script:Capabilities | ForEach-Object { Protect-Object $_ } | Export-Csv -LiteralPath $fCap -NoTypeInformation -Encoding UTF8
} else {
    Set-Content -LiteralPath $fCap -Value 'famille,nom,version,chemin,etat,preuve,statut_verification' -Encoding UTF8
}

$duree = ((Get-Date) - $script:StartedAt).TotalMinutes
# R5 : profondeur de serialisation elevee. La profondeur 8 tronquait silencieusement.
$jsonDepth = 100
$synthese = @{
    script = 'AUDIT_PHASE3_PRODUCTION_WORKSTATION'
    version = $script:ScriptVersion
    empreinte_script = $scriptHash
    machine = $env:COMPUTERNAME
    utilisateur = $env:USERNAME
    debut = $script:StartedAt.ToString('yyyy-MM-dd HH:mm:ss')
    duree_minutes = [math]::Round($duree, 2)
    statut_rapport = $script:ReportStatus
    racines = @($validRoots.ToArray())
    limites = @($script:Limits.ToArray())
    plafonds_atteints = @($script:Ceilings.ToArray())
    erreurs = @($script:Errors.ToArray())
    verification_json = @{ profondeur = $jsonDepth; relecture = 'non effectuee'; perte_detectee = $false; ecarts = @() }
    compteurs = @{
        fichiers_parcourus = $script:FilesSeen
        indices = $script:Evidence.Count
        candidats = $candidats.Count
        ressources = $script:Resources.Count
        secrets_detectes_non_lus = $script:Secrets.Count
        processus_retenus = $script:Procs.Count
        services_retenus = $script:Svcs.Count
        ports_retenus = $script:Ports.Count
        taches_retenues = $script:Tasks.Count
        conteneurs = $script:Containers.Count
        depots = $script:Repos.Count
        logiciels_inventories = $script:Inventory.Count
        capacites = $script:Capabilities.Count
        racines_decouvertes = $script:DiscoveryRoots.Count
        versions_verifiees = $script:VersionsVerifiees
        versions_non_verifiees = $script:VersionsNonVerifiees
        elements_materiels = $script:Hardware.Count
    }
    materiel = @($script:Hardware.ToArray())
    racines_decouvertes = @($script:DiscoveryRoots.ToArray())
    capacites_par_famille = $(if ($script:Capabilities.Count -gt 0) { ($script:Capabilities | Group-Object -Property famille | ForEach-Object { @{ famille = $_.Name; nombre = $_.Count } }) } else { @() })
    inventaire_par_source = $(if ($script:Inventory.Count -gt 0) { ($script:Inventory | Group-Object -Property source | ForEach-Object { @{ source = $_.Name; nombre = $_.Count } }) } else { @() })
    processus = @($script:Procs.ToArray())
    services = @($script:Svcs.ToArray())
    ports = @($script:Ports.ToArray())
    taches = @($script:Tasks.ToArray())
    conteneurs = @($script:Containers.ToArray())
    environnement_conteneurs = $script:ContainerEnv
    depots = @($script:Repos.ToArray())
    secrets_presence = @($script:Secrets.ToArray())
    avertissement = 'Aucun element de ce rapport ne qualifie automatiquement un systeme d orchestration. Les statuts sont FAIT OBSERVE, CANDIDAT ou NON VERIFIE.'
}
$typeSynth = 'null'
if ($null -ne $synthese) { $typeSynth = ($synthese.GetType().Name + ' / proprietes=' + @($synthese.PSObject.Properties).Count) }
Write-Log ('  controle synthese : ' + $typeSynth)

$jsonWritten = $false
try {
    $json = $synthese | ConvertTo-Json -Depth $jsonDepth
    Set-Content -LiteralPath $fSynth -Value $json -Encoding UTF8 -ErrorAction Stop
    $jsonWritten = $true
    Write-Log ('  synthese JSON ecrite : ' + $fSynth + ' (' + $json.Length + ' caracteres)')
} catch {
    $script:ReportStatus = 'PARTIEL'
    Add-Limit -Message 'Echec de la synthese JSON' -Ceiling
    Write-Log -Message ('  ECHEC de la synthese JSON : ' + $_.Exception.Message) -Level 'ERREUR'
    Add-Content -LiteralPath $fJournal -Value ('# ECHEC JSON : ' + $_.Exception.Message) -Encoding UTF8 -ErrorAction SilentlyContinue
}

# R5 : verification par relecture effective du fichier produit (ConvertFrom-Json).
# Toute perte d information detectee => PARTIEL + plafond identifie + reecriture.
function Get-CountSafe {
    param($Value)
    # R5 : comptage semantique. ConvertTo-Json (PS 5.1) serialise @() en {} :
    # un tableau vide relu devient un PSCustomObject vide. Sans ce correctif,
    # la verification produirait un faux "perte de donnees" sur toute liste vide.
    if ($null -eq $Value) { return 0 }
    if ($Value -is [System.Collections.IDictionary]) { return $Value.Count }
    if ($Value -is [System.Management.Automation.PSCustomObject]) { return @($Value.PSObject.Properties).Count }
    if ($Value -is [string]) { return 1 }
    if ($Value -is [System.Collections.IEnumerable]) { return @($Value).Count }
    return 1
}
if ($jsonWritten) {
    $relecture = $null
    try {
        $brut = Get-Content -LiteralPath $fSynth -Raw -ErrorAction Stop
        $relecture = ConvertFrom-Json -InputObject $brut -ErrorAction Stop
    } catch { $relecture = $null }

    if ($null -eq $relecture) {
        $script:ReportStatus = 'PARTIEL'
        Add-Limit -Message 'Perte de donnees JSON : relecture impossible' -Ceiling
        Write-Log -Message '  VERIFICATION JSON : relecture impossible (perte de donnees)' -Level 'ERREUR'
        $verifOk = $false
        $ecarts = New-Object System.Collections.Generic.List[string]
        $ecarts.Add('relecture impossible')
    } else {
        $ecarts = New-Object System.Collections.Generic.List[string]
        $nbAttendu = @($synthese.Keys).Count
        $nbObtenu = @($relecture.PSObject.Properties).Count
        if ($nbObtenu -ne $nbAttendu) { $ecarts.Add('proprietes racine ' + $nbObtenu + '/' + $nbAttendu) }
        foreach ($k in @('racines','limites','plafonds_atteints','erreurs','processus','services','ports','taches','conteneurs','depots','secrets_presence','materiel','racines_decouvertes','capacites_par_famille','inventaire_par_source')) {
            $a = Get-CountSafe $synthese[$k]
            $b = Get-CountSafe $relecture.$k
            if ($a -ne $b) { $ecarts.Add('liste ' + $k + ' ' + $b + '/' + $a) }
        }
        foreach ($k in @('fichiers_parcourus','indices','candidats','ressources','secrets_detectes_non_lus','processus_retenus','services_retenus','ports_retenus','taches_retenues','conteneurs','depots','logiciels_inventories','capacites','racines_decouvertes','versions_verifiees','versions_non_verifiees','elements_materiels')) {
            $a = [int]$synthese['compteurs'][$k]
            $b = [int]$relecture.compteurs.$k
            if ($a -ne $b) { $ecarts.Add('compteur ' + $k + ' ' + $b + '/' + $a) }
        }
        $verifOk = ($ecarts.Count -eq 0)
        if (-not $verifOk) {
            $script:ReportStatus = 'PARTIEL'
            Add-Limit -Message ('Perte de donnees JSON : ' + ($ecarts -join ' ; ')) -Ceiling
            Write-Log -Message ('  VERIFICATION JSON : ecarts detectes - ' + ($ecarts -join ' ; ')) -Level 'ERREUR'
        } else {
            Write-Log ('  VERIFICATION JSON : relecture OK (profondeur=' + $jsonDepth + ', proprietes=' + $nbObtenu + ', 0 perte)')
        }
    }

    # Reecriture avec le statut et l etat de verification reellement constates.
    $synthese['verification_json'] = @{
        profondeur = $jsonDepth
        relecture = $(if ($verifOk) { 'OK' } else { 'ECART' })
        perte_detectee = (-not $verifOk)
        ecarts = @($ecarts.ToArray())
    }
    $synthese['plafonds_atteints'] = @($script:Ceilings.ToArray())
    $synthese['statut_rapport'] = $script:ReportStatus
    try {
        $json2 = $synthese | ConvertTo-Json -Depth $jsonDepth
        Set-Content -LiteralPath $fSynth -Value $json2 -Encoding UTF8 -ErrorAction Stop
        Write-Log '  synthese JSON reecrite avec le statut final'
    } catch {
        $script:ReportStatus = 'PARTIEL'
        Add-Limit -Message 'Echec de la reecriture de la synthese JSON' -Ceiling
        Write-Log -Message ('  ECHEC de la reecriture JSON : ' + $_.Exception.Message) -Level 'ERREUR'
    }
}

Write-Log '--- fin du run ---'
Write-Log ('  duree             : ' + [math]::Round($duree, 2) + ' minutes')
Write-Log ('  limites atteintes : ' + $(if ($script:Limits.Count -gt 0) { ($script:Limits -join ' | ') } else { 'aucune' }))
Write-Log ('  plafonds atteints : ' + $(if ($script:Ceilings.Count -gt 0) { ($script:Ceilings -join ' | ') } else { 'aucun' }))
Write-Log ('  erreurs interceptees : ' + $(if ($script:Errors.Count -gt 0) { ($script:Errors -join ' | ') } else { 'aucune' }))
Write-Log ('  statut du rapport : ' + $script:ReportStatus)
Add-Content -LiteralPath $fJournal -Value ('# fin du run - statut du rapport : ' + $script:ReportStatus) -Encoding UTF8 -ErrorAction SilentlyContinue

Write-Host ''
Write-Host '=== AUDIT TERMINE ===' -ForegroundColor Cyan
Write-Host ('  fichiers parcourus : ' + $script:FilesSeen)
Write-Host ('  indices collectes  : ' + $script:Evidence.Count)
Write-Host ('  candidats          : ' + $candidats.Count)
Write-Host ('  ressources         : ' + $script:Resources.Count)
Write-Host ('  secrets (non lus)  : ' + $script:Secrets.Count)
Write-Host ('  materiel           : ' + $script:Hardware.Count + ' elements')
Write-Host ('  logiciels          : ' + $script:Inventory.Count)
Write-Host ('  capacites          : ' + $script:Capabilities.Count)
Write-Host ('  racines decouvertes: ' + $script:DiscoveryRoots.Count)
Write-Host ('  versions verifiees : ' + $script:VersionsVerifiees + ' / non verifiees : ' + $script:VersionsNonVerifiees)
Write-Host ('  plafonds atteints  : ' + $(if ($script:Ceilings.Count -gt 0) { ($script:Ceilings -join ' | ') } else { 'aucun' }))
Write-Host ('  erreurs            : ' + $(if ($script:Errors.Count -gt 0) { ($script:Errors -join ' | ') } else { 'aucune' }))
Write-Host ('  statut du rapport  : ' + $script:ReportStatus)
Write-Host ('  sorties            : ' + $OutDir)
Write-Host ''
Write-Host 'RAPPEL : aucun candidat n est qualifie de systeme d orchestration par ce script.' -ForegroundColor Yellow
Write-Host 'La qualification finale repose sur les preuves et une validation humaine.' -ForegroundColor Yellow

}   # fin du bloc finally





