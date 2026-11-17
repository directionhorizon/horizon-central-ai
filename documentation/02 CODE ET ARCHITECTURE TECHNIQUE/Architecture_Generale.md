# Architecture générale

Architecture hybride organisée autour de trois espaces :

- PC Windows : environnement principal d'exécution.
- Google Drive : mémoire persistante et suivi des informations.
- GitHub privé : code source, documentation versionnée et historique.

L'architecture sépare le cœur de l'assistant, les outils, les intégrations et les espaces de mémoire.

Elle doit rester modulaire, évolutive et indépendante d'un fournisseur unique lorsque cela est possible.
