-- Nettoyage : retire la table de test de la CI/CD, puis recharge le cache de l'API.
drop table if exists ci_check;
notify pgrst, 'reload schema';
