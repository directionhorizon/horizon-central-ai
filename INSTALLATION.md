# Installation et reprise sur un autre PC

Guide pour installer HORIZON CENTRAL AI sur une nouvelle machine (ou un serveur)
et reprendre le travail exactement là où il en est.

## 1. Prérequis

- **Git**
- **Node.js ≥ 20** et npm
- **Python ≥ 3.12**

## 2. Récupérer le code

Le dépôt est **privé** : connecte-toi d'abord au compte GitHub `directionhorizon`.

```powershell
git clone https://github.com/directionhorizon/horizon-central-ai.git
cd horizon-central-ai
```

## 3. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## 4. Réglages locaux (jamais versionnés)

Les secrets ne sont **pas** dans le dépôt. Copie le gabarit puis remplis-le :

```powershell
copy .env.example .env
```

À renseigner dans `backend/.env` :

| Variable | Rôle |
| --- | --- |
| `HORIZON_ADMIN_TOKEN` | jeton d'administration (protège les écritures) |
| `HORIZON_DATABASE_PATH` | chemin de la base (par défaut `./data/horizon.db`) |
| `HORIZON_WORKSPACE_DIR` | espace de travail autorisé des « mains » |

## 5. Interface

```powershell
cd ..
npm install
npm run build
```

## 6. Restaurer la base versionnée (reprise de l'état exact)

La base **active** (binaire `.db`) n'est jamais versionnée. À la place, un
**instantané JSON** versionné (`backend/seed/horizon_seed.json`) permet de
restaurer les données : projets, orchestrateurs, agents (FIRST AGENTIC SYSTEM),
mains (51), compétences (123), missions, documents, réglages.

1. Démarrer une fois le backend pour créer le schéma (voir §7).
2. Arrêter, puis restaurer :

```powershell
cd backend
.venv\Scripts\python tools\import_snapshot.py --in seed\horizon_seed.json
```

L'import est **idempotent** : il insère ou remplace par clé primaire, sans rien
supprimer. Aucun secret n'y figure (les colonnes sensibles sont masquées).

### Mettre à jour l'instantané versionné (depuis le PC où tu travailles)

```powershell
cd backend
.venv\Scripts\python tools\export_snapshot.py --out seed --name horizon_seed.json
git add seed/horizon_seed.json
git commit -m "chore(seed): mise a jour de l'instantane de la base"
git push
```

L'export est **non destructif** : lecture seule, aucune écriture, aucun appel réseau.

## 7. Lancer

```powershell
cd backend
.venv\Scripts\python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Puis ouvrir `http://127.0.0.1:8000`.

## 8. Points importants

- **Hermes n'est pas nécessaire** : FIRST AGENTIC SYSTEM est **natif** dans HORIZON.
- **Aucun secret dans Git** : `backend/.env` est ignoré ; les clés API ne sont
  jamais stockées en base (seul le *nom* de la variable est enregistré).
- **Données locales** : la base active et l'espace de travail sont propres à
  chaque machine ; utilise l'instantané (§6) pour les transporter.
- **Mise à jour du serveur** : un `git push` sur `main` déclenche le déploiement
  automatique sur le VPS (build + redémarrage).
