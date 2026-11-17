# MISSION : CONCEPTION ET CRÉATION DES PREMIÈRES BASES DE DONNÉES DE HORIZON CENTRAL AI

**Projet :** HORIZON CENTRAL AI  
**Composant central :** HORIZON CORE  
**Document :** HORIZON DATA ARCHITECTURE  
**Version :** 0.2 — Complément : matérialisation du système d'orchestration

> Copie de référence provisoire. Source officielle unique à établir dans le dépôt de gouvernance. Ne pas dupliquer.

## 1. OBJECTIF GÉNÉRAL

Concevoir le système de gestion des données de HORIZON CENTRAL AI et préparer la création de ses premières bases de données.

Le travail ne consiste pas simplement à créer des tables SQL.

Il consiste à établir une architecture de données cohérente avec la philosophie, les responsabilités, les capacités et les ambitions de HORIZON CENTRAL AI.

L'architecture doit pouvoir évoluer sans remettre en cause les principes fondamentaux du système.

## 2. RESPECTER L'ARCHITECTURE EXISTANTE

Avant toute proposition technique ou création :

- Examiner l'architecture réelle de HORIZON CENTRAL AI.
- Identifier les composants effectivement opérationnels.
- Identifier les fonctionnalités disponibles et celles qui restent à développer.
- Examiner les mécanismes de mémoire, de stockage et de communication existants.
- Identifier les technologies déjà utilisées.
- Distinguer les fonctionnalités opérationnelles des fonctionnalités simplement envisagées.

Ne jamais attribuer à HORIZON CENTRAL AI une capacité qui n'a pas été vérifiée.

Ne pas reconstruire inutilement les composants existants.

Ne pas remplacer les systèmes externes spécialisés déjà utilisés par HORIZON.

Toute proposition doit tenir compte de la réalité technique du projet.

## 3. PHILOSOPHIE GÉNÉRALE DES DONNÉES

L'écosystème repose sur plusieurs systèmes d'orchestration indépendants, supervisés par HORIZON CORE.

Chaque système d'orchestration est responsable de l'ensemble des données produites et utilisées dans son environnement.

Chaque système possède sa propre base de données.

À l'intérieur de cette base, chaque projet dispose d'un espace de données isolé.

Les projets ne doivent donc pas nécessiter systématiquement une nouvelle infrastructure de base de données.

L'organisation doit permettre de mutualiser les ressources lorsque cela est pertinent, sans sacrifier l'isolation des projets.

## 4. INDÉPENDANCE DES PROJETS

Chaque projet doit pouvoir être administré indépendamment des autres projets de son système d'orchestration.

Cette indépendance doit notamment permettre :

- La sauvegarde individuelle.
- La restauration individuelle.
- Le déplacement individuel.
- L'évolution indépendante.
- La suppression contrôlée.

Une opération sur un projet ne doit pas compromettre les autres projets.

## 5. LIBERTÉ D'ORGANISATION DES DONNÉES

Les systèmes d'orchestration n'ont pas nécessairement les mêmes missions, les mêmes domaines d'activité ou les mêmes besoins.

Par conséquent :

- Ne pas imposer une structure universelle de données à tous les systèmes.
- Laisser chaque système définir les catégories et les structures adaptées à ses missions.
- Préserver une organisation cohérente à l'intérieur de chaque projet.
- Permettre l'évolution des structures sans compromettre les autres projets.

HORIZON CORE doit pouvoir comprendre et superviser l'ensemble sans imposer une organisation métier identique à tous.

## 6. RESPONSABILITÉ DE HORIZON CORE

HORIZON CORE est le superviseur en chef de l'ensemble de l'écosystème.

Il ne doit pas être réduit à un simple annuaire de bases de données.

Il doit disposer d'une compréhension transversale de la structure :

- Connaître les systèmes d'orchestration.
- Connaître les projets qu'ils administrent.
- Comprendre les relations entre les systèmes.
- Connaître les responsabilités de chacun.
- Pouvoir consulter les informations nécessaires à sa mission de supervision.
- Comprendre les historiques, les décisions et les événements importants.
- Détecter les incohérences et les conflits.
- Intervenir lorsque les systèmes d'orchestration ne parviennent pas à résoudre une difficulté.

HORIZON CORE doit être capable de prendre des décisions éclairées à l'échelle de toute la structure.

Il n'est pas nécessaire qu'il conserve physiquement toutes les données, mais il doit pouvoir les retrouver et les comprendre lorsque sa mission l'exige.

## 7. MÉMOIRE ET HISTORIQUE

L'orchestrateur joue le rôle de manager auprès de ses agents.

Il doit disposer d'une connaissance suffisamment actualisée des activités, des opérations et des historiques de son environnement.

Les agents ne doivent pas être obligés de rechercher individuellement et systématiquement dans toutes les anciennes opérations.

L'orchestrateur doit pouvoir exploiter les informations historiques nécessaires à la continuité de son travail.

HORIZON CORE doit également disposer d'une compréhension transversale des historiques des différents systèmes afin de pouvoir superviser et arbitrer.

La durée de conservation des données doit pouvoir être définie et adaptée aux besoins et aux configurations.

## 8. COMMUNICATION ENTRE SYSTÈMES

Les systèmes d'orchestration doivent rester indépendants.

Cependant, ils peuvent être amenés à collaborer.

Toute collaboration nécessitant un accès aux données d'un autre système doit respecter les règles suivantes :

1. Les orchestrateurs concernés définissent les besoins de collaboration.
2. HORIZON CORE examine la demande.
3. HORIZON CORE donne lui-même l'autorisation.
4. Les accès sont limités aux données autorisées.
5. Les autorisations restent actives jusqu'à leur révocation.

Aucun système ne doit pouvoir accéder librement aux données d'un autre système.

## 9. RÈGLES D'ACCÈS INTERNES

Le principe de fonctionnement retenu est le suivant :

À l'intérieur d'un même système d'orchestration, les agents peuvent accéder aux données des autres agents dans le cadre des règles de fonctionnement de leur environnement.

Entre deux systèmes d'orchestration différents, l'accès est interdit par défaut.

Une autorisation explicite de HORIZON CORE est obligatoire pour permettre un partage.

Les mécanismes techniques permettant de garantir cette séparation devront être définis pendant la conception.

## 10. ARBITRAGE ET GOUVERNANCE

Lorsqu'un désaccord apparaît entre deux systèmes d'orchestration et que leurs responsables ne parviennent pas à trouver une solution :

HORIZON CORE doit pouvoir :

- Consulter les informations nécessaires.
- Examiner les historiques et les décisions concernées.
- Comprendre les responsabilités des systèmes.
- Analyser les conséquences des différentes possibilités.
- Prendre une décision d'arbitrage.
- Coordonner son application.

HORIZON CORE détient donc une autorité supérieure de gouvernance dans l'écosystème.

## 11. PRINCIPES TECHNIQUES

Les choix technologiques doivent servir l'architecture définie.

Supabase et PostgreSQL constituent des pistes technologiques à étudier pour la mise en œuvre.

Ils ne doivent cependant pas dicter la philosophie du système.

L'agent chargé de la conception devra notamment étudier :

- L'organisation des bases par système d'orchestration.
- L'isolation des projets.
- La gestion des accès.
- La gestion des historiques.
- La sauvegarde et la restauration.
- Les échanges entre systèmes.
- La supervision centrale.
- L'évolution des infrastructures.

Ne pas multiplier les bases physiques sans justification.

Ne pas mutualiser des données lorsque cela compromet leur sécurité ou leur indépendance.

## 12. EXIGENCES DE RÉALISATION

Le travail devra suivre cet ordre :

**Phase A — Audit**
Établir un état réel de l'architecture existante.

**Phase B — Conception**
Produire une architecture détaillée conforme aux principes validés.

**Phase C — Validation**
Présenter les choix techniques, leurs conséquences et les points encore ouverts avant toute création.

**Phase D — Création**
Créer les premières bases et structures nécessaires, uniquement après validation de la conception.

**Phase E — Vérification**
Tester l'isolation des projets, les autorisations, la sauvegarde, la restauration et les mécanismes de communication.

**Phase F — Documentation**
Documenter les structures créées, leurs responsabilités, leurs dépendances et leurs modalités d'administration.

## 13. RÈGLES DE CONDUITE DE L'AGENT

- Ne jamais confondre une hypothèse et une décision validée.
- Ne jamais prendre une décision architecturale importante à la place du concepteur.
- Expliquer les propositions techniques dans un langage compréhensible.
- Signaler les limites de l'architecture actuelle.
- Privilégier une architecture évolutive et modulaire.
- Éviter les duplications et les complexités inutiles.
- Préserver les composants existants.
- Ne procéder à aucune modification destructive sans autorisation explicite.
- Présenter les résultats de chaque phase avant de passer à la suivante.

## 14. RÉSULTAT ATTENDU

Produire une architecture de données capable de soutenir durablement HORIZON CENTRAL AI, ses systèmes d'orchestration, leurs agents et leurs projets.

Les premières bases doivent constituer une fondation fiable, évolutive, sécurisée et adaptée aux capacités réelles de HORIZON.

**Principe directeur : la technologie doit s'adapter à la philosophie de HORIZON, et non l'inverse.**

IMPORTANT : Pour cette première intervention, tu es uniquement chargé d'auditer l'architecture existante de HORIZON CENTRAL AI au regard des principes de conception fournis.

NE CRÉE AUCUNE BASE DE DONNÉES.
NE MODIFIE AUCUN FICHIER.
N'INSTALLE AUCUNE DÉPENDANCE.

Examine le projet et produis un rapport détaillé sur son état réel, ses composants, ses capacités actuelles et les adaptations nécessaires pour mettre en œuvre HORIZON DATA ARCHITECTURE.

Attends une validation explicite avant toute modification ou création.


## 15. MATÉRIALISATION DU SYSTÈME D'ORCHESTRATION DANS LE MODÈLE DE DONNÉES ET LE BACKEND

### 15.1 Exigence architecturale

La notion de **système d'orchestration** doit être représentée comme une entité de premier ordre dans le modèle de données et dans le backend de HORIZON CENTRAL AI.

Cette exigence rend explicites les principes déjà établis dans ce document : les systèmes d'orchestration sont indépendants, possèdent chacun leur environnement de données, administrent leurs projets et sont supervisés par HORIZON CORE.

À terme, HORIZON CORE doit pouvoir :

- Enregistrer et identifier les systèmes d'orchestration.
- Connaître les projets administrés par chaque système.
- Comprendre les relations entre les systèmes et leurs projets.
- Connaître le système responsable d'un projet et, lorsqu'il y a lieu, les systèmes contributeurs.
- Superviser les informations nécessaires à sa mission de gouvernance.
- Contrôler les demandes de collaboration et les accès entre systèmes conformément aux règles des sections 8 et 9.

Cette capacité de supervision ne signifie pas que HORIZON CORE doit héberger physiquement toutes les données métier. Les principes de responsabilité et d'indépendance définis dans les sections 3 et 6 restent applicables.

### 15.2 Distinction des notions

Le modèle de données et le backend doivent distinguer explicitement les notions suivantes :

- **Système d'orchestration :** environnement autonome responsable de ses données et de l'administration de ses projets.
- **Orchestrateur :** responsable de la coordination des agents au sein de son environnement, conformément à la section 7.
- **Projet :** unité administrée indépendamment au sein d'un système d'orchestration, conformément aux sections 3 et 4.

Le système d'orchestration ne doit donc pas être confondu avec l'orchestrateur qui y exerce une fonction de management.

Cette distinction est conceptuelle et ne préjuge pas encore de la représentation technique qui sera retenue pour chaque entité.

### 15.3 Relations à représenter

Le modèle cible devra permettre de représenter, au minimum :

- La relation entre un système d'orchestration et les projets qu'il administre.
- L'identification du système responsable de chaque projet.
- L'identification des systèmes contributeurs lorsqu'un projet est partagé.
- Les relations entre systèmes nécessaires à la supervision et à la collaboration.
- Le rattachement des ressources à leur système et à leur projet, avec leur provenance lorsque cela est nécessaire.

Lorsqu'un deuxième système contribue à un projet, le projet doit être traité selon la procédure de projet partagé prévue par le plan intégral, notamment son exigence de déclenchement du catalyseur inter-systèmes.

La représentation de ces relations doit préserver l'indépendance des systèmes et des projets. Elle ne doit pas autoriser un accès direct et libre aux données d'un autre système.

### 15.4 Séquence de conception et de réalisation

La matérialisation de cette entité doit respecter l'ordre de réalisation suivant :

**Phase 3 — Audit du Production Workstation**

Identifier les systèmes, leurs composants et les ressources réellement disponibles dans le périmètre audité. Distinguer les systèmes existants des systèmes simplement envisagés.

**Phase 4 — Consolidation et classification**

Rattacher les ressources inventoriées aux systèmes et projets concernés, en documentant les responsabilités, les contributeurs, la provenance et les incertitudes.

**Phase 5 — Validation des architectures cibles**

Définir et faire valider le modèle conceptuel et logique du système d'orchestration avant toute migration. Cette conception doit notamment préciser :

- Les entités et leurs responsabilités.
- Les relations entre systèmes, orchestrateurs, projets et ressources.
- La désignation du système responsable et des contributeurs.
- Les informations administratives nécessaires à HORIZON CORE.
- Les mécanismes d'isolation et d'autorisation.
- La traduction de ce modèle dans les architectures cibles Supabase, GitHub et Google Drive.

Aucune structure technique ne doit être créée avant la validation de cette architecture cible.

**Phases 6 à 10 — Préparation, migrations et vérifications**

Préparer les sauvegardes, migrer les données selon l'architecture validée, puis vérifier les rattachements, les identifiants, les responsabilités, la provenance et les autorisations.

**Phase 11 — Évolutions backend**

Implémenter le modèle validé dans le backend de HORIZON CENTRAL AI. Cette évolution doit couvrir les modèles de données, les relations, les interfaces API, les services, les contrôles d'accès et la journalisation nécessaires à la gestion et à la supervision des systèmes d'orchestration.

Le développement ne doit pas inventer une structure indépendante de l'architecture validée en phase 5.

**Phase 12 — Catalyseur inter-systèmes**

S'appuyer sur les entités et relations implémentées pour gérer les projets partagés, les contributeurs, les autorisations, les événements de collaboration et les éventuels arbitrages de HORIZON CORE.

### 15.5 Décisions techniques à valider avant réalisation

La présente exigence fixe la nécessité de représenter le système d'orchestration comme une entité de premier ordre. Elle ne choisit pas à elle seule sa mise en œuvre technique.

Restent notamment à concevoir et à valider en phase 5 :

- La représentation physique et logique des entités dans les bases de données.
- L'articulation entre le registre central de HORIZON CORE et les bases propres aux systèmes.
- Les identifiants et relations entre systèmes, orchestrateurs, projets et ressources.
- Les métadonnées que HORIZON CORE doit conserver ou consulter.
- Les règles d'accès, d'autorisation, de révocation et de traçabilité.
- Les modalités de migration depuis les structures actuellement existantes.

Aucune décision de schéma, de table, de nommage technique ou de déploiement n'est considérée comme validée par la seule insertion de cette exigence.

### 15.6 Vérifications attendues

La conception puis l'implémentation devront permettre de vérifier que :

- HORIZON CORE peut identifier les systèmes d'orchestration enregistrés.
- Les projets sont rattachés au système responsable.
- Les systèmes contributeurs d'un projet partagé sont identifiables.
- Les relations et responsabilités peuvent être consultées et auditées.
- Les accès inter-systèmes restent interdits par défaut et nécessitent une autorisation de HORIZON CORE.
- L'isolation et l'indépendance des données des systèmes et des projets sont préservées.

**Exigence directrice : le système d'orchestration doit exister comme entité explicite dans le modèle de données et le backend de HORIZON CENTRAL AI. Sa structure doit être définie et validée en phase 5, avant les migrations, puis son fonctionnement doit être implémenté en phase 11.**
