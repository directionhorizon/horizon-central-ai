-- Force PostgREST à recharger son cache de schéma ; rend visibles les
-- nouvelles tables créées par migration. À inclure après tout DDL.
notify pgrst, 'reload schema';
