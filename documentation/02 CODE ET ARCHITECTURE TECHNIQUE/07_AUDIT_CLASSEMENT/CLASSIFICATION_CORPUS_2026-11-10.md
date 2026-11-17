# CLASSIFICATION DU CORPUS LOCAL — HORIZON CENTRAL AI
**Version 0.1 — 10 novembre 2026 — étape 3 du §12 (consolidation et classification)**
**Méthode** : inventaire lecture seule, sans déplacement, sans suppression, sans renommage.
**Pièces jointes** : `INVENTAIRE_CONSOLIDE_2026-11-10.csv` (241 lignes, chemin/taille/date/extension).

---

## 1. Périmètre et exclusions

Périmètre mesuré : `C:\Users\hp\HORIZON LOCAL AI` (les 4 piliers + racine).

**Exclus du décompte** (volume technique, non gouverné) : `node_modules` (32 241 fichiers / 366,7 Mo),
`.venv`, `__pycache__`, `dist`, `.git`. Ces dossiers sont **reconstruits**, pas conservés : ils ne
constituent pas des ressources à classer.

## 2. Volumétrie réelle

| Emplacement | Fichiers |
|---|---|
| `02 CODE ET ARCHITECTURE TECHNIQUE` | **204** |
| `01 FONCTIONNEMENT` | 17 |
| `03 MÉMOIRE LOCALE` | 10 |
| `04 MÉMOIRE EN LIGNE` | 9 |
| `README.md` (racine) | 1 |
| **Total** | **241 fichiers / 3,6 Mo** |

Le pilier 02 concentre 85 % des fichiers : c'est cohérent avec un projet en phase de construction, mais
cela signifie aussi que **les piliers 01, 03 et 04 sont quasi vides** (36 fichiers à eux trois).

## 3. Répartition par nature

| Type | Nombre | Nature | Destination logique (§3.1–3.3) |
|---|---|---|---|
| `.md` | 71 | documentation | gouvernance / documentation technique |
| `.tsx` + `.ts` | 63 | code frontend | GitHub |
| `.py` | 35 | code backend | GitHub |
| `.log` | 13 | journaux d'exécution | mémoire locale (journaux) |
| `.zip` | 12 | archives et sauvegardes | archives (jamais en dépôt de code) |
| `.json` | 9 | configuration, snapshots, manifestes | GitHub (non secret) / données localement |
| `.png` | 8 | captures d'écran | Drive (médias) |
| `.csv` | 6 | inventaires d'audit | gouvernance |
| `.bak` | 6 | sauvegardes de fichiers | à statuer (voir §6) |
| `.ps1` / `.bat` | 5 | scripts de lancement | GitHub |
| `.db` | 1 | **base SQLite locale** (`horizon.db`, 196 Ko) | **jamais dans un dépôt** |
| autres | 14 | config outillage | GitHub |

Point de vigilance immédiat : **1 base `.db`, 13 journaux, 12 archives** — soit 26 fichiers qui ne doivent
jamais partir dans un dépôt de code, sous aucun prétexte. C'est précisément ce qu'un `.gitignore`
insuffisant (83 o) laisserait passer.

## 4. Statut d'autorité par ensemble (proposition à valider)

| Ensemble | Constat | Statut proposé |
|---|---|---|
| `02_CODE_SOURCE\HORIZON_LOCAL_AI` | `App.tsx` 8 970 o, backend complet, build OK | **SOURCE AUTORITAIRE** (code) |
| `Desktop\HORIZON_TEST_1.0.0` et `Nouveau dossier\…` | `App.tsx` 2 452 o, sans `backend/horizon` | **COPIE FIGÉE** (archive) |
| `01 FONCTIONNEMENT` — sous-dossiers | 1 601 à 3 169 o : contenu réel | **SOURCE AUTORITAIRE** (fonctionnement) |
| `01 FONCTIONNEMENT` — racine | 440 à 630 o : coquilles | **À STATUER** (probable obsolète) |
| `01 FONCTIONNEMENT` — `.bak` | 226 à 616 o, aucun identique au courant | **RÉSIDU** (statut archive) |
| `06 ARCHIVES\DOCUMENTS_HISTORIQUES` | 6 docs de 336–509 o, dont **5 identiques octet pour octet** à des docs vivants | **COPIE**, pas une version antérieure |
| `06 ARCHIVES\SOURCES_ORIGINALES` | 6 zips MagicPath (76–83 Ko) | **AUTORITÉ HISTORIQUE** des interfaces |
| `06 ARCHIVES\VERSIONS` | 4 zips datés (50–59 Ko) | **VERSIONS** datées |
| `03 MÉMOIRE LOCALE\07_SAUVEGARDES` | 2 zips du 08/11 (59 Ko, 684 Ko) | **SAUVEGARDE NON VÉRIFIÉE** (aucun test de restauration) |

**Constat majeur** : `06 ARCHIVES\DOCUMENTS_HISTORIQUES` ne contient **aucune version antérieure utile** —
ce sont des copies exactes de documents encore vivants, plus un stub (`Architecture_Generale_avant_fusion.md`,
336 o). L'archive documentaire est donc **vide de valeur historique**, tout en donnant l'illusion du
contraire. C'est un point à dire clairement plutôt qu'à laisser croire.

## 5. Doublons exacts (empreinte MD5) — 9 groupes

| # | Fichiers | Taille | Décision proposée (non exécutée) |
|---|---|---|---|
| 1 | `LLMSelector.tsx` ×4 (4 pages) | 3 936 o | factoriser dans `src/components/` — **impact code, annonce préalable** |
| 2 | `SystemHeader.tsx` ×4 | 2 535 o | idem *(comptage MD5 : 4, et non 3 comme estimé plus tôt)* |
| 3 | `Integrations_API.md` : `04_INTEGRATIONS` ↔ `06 ARCHIVES` | 463 o | le vivant fait autorité ; l'archive garde le statut « copie » |
| 4 | `Plan_Implementation.md` : `07_PLANIFICATION` ↔ `06 ARCHIVES` | 509 o | idem |
| 5 | `Environnement_Windows.md` : `05_CONFIGURATION` ↔ `06 ARCHIVES` | 443 o | idem |
| 6 | `Composants_Modules.md` : `03_MODULES` ↔ `06 ARCHIVES` | 468 o | idem |
| 7 | `Architecture_Logicielle.md` : `01_ARCHITECTURE` ↔ `06 ARCHIVES` | 438 o | idem |
| 8 | `.clinerules` ↔ `.clinerules.md\HORIZON_TOKEN_OPTIMIZATION.md` | 1 608 o | voir §6.1 |
| 9 | `apres-cockpit.png` ↔ `avant-cockpit.png` | 134 953 o | voir §6.2 |

Aucune suppression, aucun déplacement. Un doublon n'est pas un déchet : c'est une **ambiguïté de source**
qu'il faut nommer avant de trancher.

## 6. Anomalies structurelles

**6.1 — `.clinerules.md` est un DOSSIER, pas un fichier.**
Il contient `HORIZON_TOKEN_OPTIMIZATION.md` (1 608 o), **identique octet pour octet** au fichier `.clinerules`.
Conséquence : la règle « optimisation de tokens » n'est **pas chargée** comme règle projet — un dossier ne
porte pas de règles. Deux entités de même nom coexistent, une seule est active.

**6.2 — Les captures « avant » et « après » cockpit sont le même fichier.**
`avant-cockpit.png` et `apres-cockpit.png` ont la même empreinte MD5. La preuve visuelle d'une
amélioration n'existe donc pas. Toute affirmation du type « avant/après vérifié » appuyée sur ces fichiers
serait fausse.

**6.3 — `01 FONCTIONNEMENT` existe en trois versions par document**, et la plus riche (sous-dossier) est la
moins visible. Lire la racine du pilier donne l'impression d'un pilier vide de contenu.

## 7. Ce que cette classification ne fait pas

Elle ne déplace rien, ne renomme rien, ne supprime rien. Elle ne déclare aucune donnée obsolète : elle
constate, elle propose, elle attend validation. Les 4 déclarations à valider : source autoritaire du code,
source autoritaire de `01 FONCTIONNEMENT`, statut des 6 stubs archivés, statut des `.bak`.

## 8. Suite — étape 4 du §12 (validation des architectures cibles)
Trois décisions conditionnent la suite : (1) modèle Supabase (schémas dédiés / `project_id` mutualisé /
hybride) ; (2) arborescence Drive par système et projet ; (3) dépôt de gouvernance (§15). Aucune n'est
engagée.

