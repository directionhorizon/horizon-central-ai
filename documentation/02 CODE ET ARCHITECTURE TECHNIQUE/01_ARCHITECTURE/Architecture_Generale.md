# Architecture générale

HORIZON LOCAL AI repose sur une architecture hybride organisée autour de trois espaces :

- PC Windows : environnement principal d'exécution.
- Google Drive : mémoire persistante et suivi des informations.
- GitHub privé : code source, documentation versionnée et historique.

L'architecture sépare clairement :
- Le cœur de l'assistant.
- Les outils et modules.
- Les intégrations externes.
- Les espaces de mémoire locale et en ligne.

Elle doit rester modulaire, évolutive et indépendante d'un fournisseur unique lorsque cela est possible.
