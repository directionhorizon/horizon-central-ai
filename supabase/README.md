# Supabase — migrations du schéma (CI/CD)

Ce dossier contient les **migrations du schéma Supabase**, versionnées dans Git.

## Principe
- Chaque changement de structure (table, colonne, politique) = **un fichier** dans
  `supabase/migrations/`, nommé `NNNN_description.sql` (ordre croissant).
- On ne modifie **jamais** une migration déjà appliquée : on en ajoute une nouvelle.
- Le schéma s'applique **automatiquement** au `push` sur `main` (voir l'une des
  deux méthodes ci-dessous).

## Méthode A — Intégration GitHub intégrée à Supabase
Dans le tableau de bord Supabase : **Project Settings → Integrations → GitHub**.
Supabase lit `supabase/migrations/` et applique les migrations à chaque push.

## Méthode B — Supabase CLI + GitHub Actions (contrôle total)
Secrets à créer dans GitHub (Settings → Secrets and variables → Actions) :
- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_PROJECT_ID` (le « project ref »)

Le workflow `.github/workflows/supabase-migrations.yml` exécute alors :
`supabase link` puis `supabase db push` à chaque push touchant `supabase/migrations/`.

## Fichiers
- `0001_initial_schema.sql` — schéma initial (22 tables), dérivé de l'architecture
  réelle. **À valider** avant première application (exigence de la politique).

> Aucun secret ne doit jamais être écrit dans ce dossier ni dans le dépôt.
