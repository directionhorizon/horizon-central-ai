# Déploiement — conditions minimales

Ce document décrit ce qui est nécessaire pour exposer HORIZON CORE hors de la
machine locale (test externe, domaine public, scan de sécurité). Il ne décrit
pas une procédure d'installation complète.

## 1. Le backend sert déjà l'interface

Un seul processus suffit : `uvicorn app:app` sert l'API **et** `dist/`.
L'URL de l'API est relative (`''` par défaut), donc aucune adresse en dur.

```powershell
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

## 2. Authentification obligatoire hors de la machine

Sans authentification, l'API refuse toute route `/api/...` (sauf
`/api/v1/health`) dès que le nom d'hôte reçu n'est pas local : réponse `503`
avec le code `auth_required_for_remote_access`.

Configurer l'un des deux mécanismes avant d'exposer :

| Variable | Usage |
| --- | --- |
| `HORIZON_ADMIN_TOKEN` | Jeton unique, repli mono-poste |
| `HORIZON_GOOGLE_CLIENT_ID` + secret | Session Google signée |

Aucune valeur de jeton n'est jamais renvoyée par l'API.

## 3. HTTPS

Le TLS se termine devant l'application (proxy inverse, tunnel, hébergeur).
L'application n'implémente pas de certificat.

- En-têtes déjà émis : `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, CSP, COOP/CORP.
- `Strict-Transport-Security` est ajouté seulement si `X-Forwarded-Proto: https`
  est transmis par le proxy.

## 4. Données

`backend/data/horizon.db` contient les données réelles : ne jamais exposer une
instance distante sur cette base. Utiliser une base dédiée :

```powershell
$env:HORIZON_DATABASE_PATH = "D:\horizon-test\horizon.db"
```

## 5. Vérifications avant exposition

```powershell
cd backend
pytest -q
```

Attendu : 82 tests verts (santé, en-têtes, garde-fou réseau, parcours projet,
service de l'interface compilée, mains et fournisseurs IA).

```powershell
npm run build
```

Attendu : compilation TypeScript et build Vite sans erreur.

## 6. Fournisseurs IA (LLM) : clés et modèles

Un seul adaptateur, compatible OpenAI : chaque fournisseur déclare une **URL de
base** et un **modèle** (`/api/v1/models`). Le test de connexion interroge
d'abord `/models`, puis retombe sur `/chat/completions` si la route n'existe
pas (cas de Gemini).

### Nommage des clés — une variable par fournisseur

| Variable | Fournisseur |
| --- | --- |
| `HORIZON_GEMINI_API_KEY` | Google Gemini |
| `HORIZON_OPENAI_API_KEY` | OpenAI |
| `HORIZON_LLM_API_KEY` | variable générique de repli |

La base ne stocke **jamais** la clé : uniquement le **nom** de la variable
(`api_key_env`). Le déploiement injecte ces valeurs depuis les secrets GitHub
(`Settings → Secrets and variables → Actions`), jamais depuis le dépôt.

### Modèles à éviter

Les modèles retirés pour les nouveaux comptes renvoient `404` (ex.
`gemini-2.5-flash`). Les modèles saturés renvoient `503` : l'adaptateur réessaie
automatiquement, puis échoue proprement. Préférer les alias stables :
`gemini-flash-lite-latest`, `gemini-2.5-flash-lite`, `gemini-3-flash-preview`.

### Changer le modèle sans redéploiement

Dans **Model Manager**, bouton **Modifier** sur la fiche : le modèle et l'URL de
base sont modifiables en ligne. Le bouton **Tester une réponse** envoie un vrai
appel au modèle et affiche la réponse (aucune réponse n'est simulée en cas
d'échec).
