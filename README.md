# HORIZON CENTRAL AI — livraison consolidée du 7 novembre 2026

**Version du livrable : 1.0.0 — consolidation des travaux v0.1 à v0.7**

Cette livraison rassemble dans une seule archive les évolutions précédemment distribuées séparément. Il n'est pas nécessaire de récupérer les archives v0.3, v0.4 ou v0.6 : leurs changements retenus sont inclus dans cette version consolidée.

## 1. Les six espaces intégrés

1. Main Workbench
2. Model Manager
3. Agents & Tools Catalog
4. Knowledge & Memory Hub
5. AI Control Center
6. System Monitor

Les six espaces sont accessibles depuis une navigation principale commune. Les composants issus des six exports MagicPath sont conservés dans leurs dossiers respectifs.

## 2. Fonctionnalités effectivement présentes

- Application frontend Vite + React + TypeScript.
- Navigation commune entre les six espaces.
- Contexte conversationnel partagé entre Main Workbench et AI Control Center.
- Persistance locale de la session côté navigateur (cache local), selon l'implémentation livrée.
- API FastAPI avec stockage SQLite pour les sessions et messages.
- Routes de santé et de capacités.
- Contrat d'API et exemple de registre des capacités.
- Les réponses IA ne sont pas simulées : sans LLM raccordé, l'API enregistre le message et renvoie `accepted_no_model`.

## 3. Limites connues — ne pas confondre interface et intégration réelle

Les éléments suivants ne sont pas encore connectés ou validés de bout en bout :

- LLM Manager : sélection et routage multi-fournisseurs réels, tests de connexion, fallback effectif.
- Réponses de modèles IA dans la conversation.
- Google Drive : synchronisation de la mémoire en ligne.
- GitHub : synchronisation du dépôt privé.
- Exécution des agents et outils externes.
- Mesures système Windows réelles.
- Synchronisation entre plusieurs appareils.
- Authentification et gestion multi-utilisateur de production.

Les données d'exemple qui subsistent dans les écrans doivent être considérées comme des données de démonstration, et non comme des mesures ou connexions actives.

## 4. Architecture de stockage HORIZON à conserver

- Windows : environnement principal d'exécution.
- GitHub privé : dépôt de référence du code source et de la documentation versionnée.
- Google Drive : mémoire persistante et continuité des projets.

Cette archive est le livrable applicatif à placer dans le pilier `02 CODE ET ARCHITECTURE TECHNIQUE`. Elle ne remplace pas les rôles respectifs de GitHub et Google Drive.

## 5. Emplacement local cible

Après validation de l'arborescence du pilier technique :

`C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_LOCAL_AI`

Les sources originales exportées depuis MagicPath restent conservées séparément dans :

`C:\Users\hp\Desktop\Nouveau dossier`

Ne pas écraser ni supprimer les exports originaux.

## 6. Démarrage — frontend

Prérequis : Node.js compatible avec Vite 6 et npm.

Depuis le dossier de l'application :

```powershell
npm install
npm run dev
```

Vérification de compilation :

```powershell
npm run build
```

## 7. Démarrage — API locale

Depuis le dossier `backend` :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Documentation API : `http://127.0.0.1:8000/docs`

La connexion frontend/backend doit être considérée comme une étape de raccordement à finaliser et à tester dans l'environnement Windows cible. Le backend ne génère pas de réponses IA.

## 8. Vérifications réalisées pour cette livraison

- Présence des six composants de page : vérifiée.
- Présence des fichiers d'entrée React, du contexte partagé et du backend : vérifiée.
- Syntaxe Python du backend : contrôlée séparément.
- Intégrité ZIP : contrôlée.
- Build TypeScript/Vite : non certifié dans cet environnement, car les dépendances npm ne sont pas installées ici.
- Tests d'exécution sur le PC Windows cible : restent à réaliser.

## 9. Règle de version

Cette archive remplace les livraisons intermédiaires v0.1 à v0.7 pour la reprise du projet. Conserver les anciennes archives uniquement comme historique si elles sont déjà téléchargées ; pour la suite du travail, utiliser la version 1.0.0 du 7 novembre 2026.

## 10. Mode bureau Windows et fonctionnement Offline-First (ajout 9 novembre 2026)

HORIZON peut être lancé comme une application de bureau locale, sans Internet :

```
Double-clic sur HORIZON.bat (ou le raccourci « HORIZON CENTRAL AI » du Bureau)
   └─ HORIZON.ps1 démarre le moteur local (Uvicorn) s'il n'est pas déjà actif,
      attend /api/v1/health puis ouvre une fenêtre Edge/Chrome en mode
      application (sans barre d'adresse, profil dédié).
HORIZON-Stop.ps1 arrête proprement le moteur (aucune donnée supprimée).
```

Principe :

- Le backend FastAPI sert lui-même l'interface compilée (`dist/`) : un seul
  processus local, aucune ressource externe, aucun serveur distant requis.
- Les données restent dans la base SQLite locale `backend/data/horizon.db`.
- La connexion Internet est **optionnelle** : elle active les fournisseurs IA
  distants et la synchronisation Supabase.
- Chaque écriture métier (projets, orchestrateurs, missions, documents) est
  inscrite dans une file locale (`sync_outbox`). La synchronisation est manuelle
  (`/sync`) ou automatique si `HORIZON_SYNC_AUTO=1`.
- Un conflit local/distant est consigné dans `sync_conflicts` et n'est **jamais**
  écrasé silencieusement ; sa résolution reste une action humaine.

Page dédiée : `/sync` (« Synchronisation ») dans la navigation.
Architecture détaillée, contrats et limites : `docs/OFFLINE_FIRST_ARCHITECTURE.md`.

Variables concernées (dans `backend/.env`, jamais dans l'interface) :
`HORIZON_SUPABASE_URL`, `HORIZON_SUPABASE_KEY`, `HORIZON_CONNECTIVITY_PROBE`,
`HORIZON_SYNC_AUTO`, `HORIZON_SYNC_INTERVAL_S`.


## 11. Poste de pilotage central et thèmes (ajout 9 novembre 2026)

L'application s'ouvre désormais sur **`/cockpit`**, un poste de pilotage unique :

- **centre** : conversation permanente avec HORIZON CORE et planification réelle
  (`/api/v1/core/plan`, qui répond `no_model` tant qu'aucun modèle n'est vérifié) ;
- **gauche** : projets, missions du projet, historique des sessions, accès rapide ;
- **droite** : orchestrateurs, ressources, progression, état réel des connexions ;
- **tiroirs** : Modèles, Mémoire, Outils & agents, Sécurité, Synchronisation,
  Supervision, Paramètres — ils réutilisent les pages existantes, aucune
  fonctionnalité n'a été retirée.

Les autres routes (`/workbench`, `/projects`, `/models`, `/orchestrators`,
`/catalog`, `/memory`, `/control`, `/monitor`, `/sync`) restent accessibles.

**Thèmes** : Clair, Sombre (défaut), Confort visuel, Contraste élevé,
Automatique (préférences système, puis horaires personnalisés si activés),
Personnalisé ; six palettes d'accent (Cyan, Bleu, Violet, Émeraude, Ambre,
Rose). Sélection instantanée depuis l'en-tête ou le tiroir Paramètres ;
préférence conservée après redémarrage (`localStorage`, clé
`horizon-local-ai:theme:v1`). Les pages existantes suivent le thème sans avoir
été réécrites.

Détails, tests exécutés et limites : `docs/UI_COCKPIT_AND_THEMES.md`.

