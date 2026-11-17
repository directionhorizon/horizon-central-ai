# HORIZON CENTRAL AI --- Politique de gouvernance des données administratives

**Référence :** HCA-DATA-GOV-ADMIN\
**Version :** 1.0 --- 11 novembre 2026\
**Statut :** Document de conception --- validation humaine requise avant
mise en production\
**Document associé :** HORIZON CENTRAL AI --- Politique de gouvernance
et philosophie d'architecture des données v0.4\
**Document d'architecture associé :** HORIZON DATA ARCHITECTURE v0.3

## 1. Objet et portée

La présente politique définit les règles de gouvernance applicables aux
**données administratives de HORIZON CENTRAL AI**, sous la
responsabilité de HORIZON CORE.

Elle complète la politique générale de gouvernance des données. Elle ne
la remplace pas et ne constitue pas une seconde politique générale.

Elle encadre les informations nécessaires à l'administration centrale de
l'écosystème : identification et référencement des systèmes
d'orchestration, identification des orchestrateurs responsables,
registre administratif des projets, relations et responsabilités entre
systèmes, paramètres centraux, identités et autorisations, décisions de
gouvernance et traçabilité administrative.

Elle s'applique aux données administratives conservées ou référencées
par HORIZON CORE, quel que soit leur support technique : Supabase,
GitHub, Google Drive ou tout autre support validé.

Cette politique ne gouverne pas le contenu métier des projets ni les
données produites dans le fonctionnement quotidien des systèmes
d'orchestration. Ces données restent soumises à la politique générale et
aux règles opérationnelles propres à chaque système.

## 2. Place dans le dispositif documentaire

Le dispositif de gouvernance des données de HORIZON CENTRAL AI comporte
deux niveaux complémentaires :

1.  **Politique générale de gouvernance et philosophie d'architecture
    des données** : principes communs, responsabilités, classification
    générale, sécurité, cycle de vie, partage inter-systèmes,
    conservation, sauvegarde, migration et exigences transversales.
2.  **Politique de gouvernance des données administratives** :
    application de ces principes au périmètre administratif central de
    HORIZON CORE.

La gouvernance des données opérationnelles relève de la politique
générale et des déclinaisons propres aux systèmes d'orchestration. La
présente politique ne doit pas être interprétée comme une normalisation
de leurs structures opérationnelles.

En cas de conflit, les obligations légales et contractuelles applicables
prévalent, puis la politique générale de gouvernance des données. La
présente politique précise les règles du domaine administratif sans
affaiblir les exigences générales.

## 3. Philosophie de gouvernance administrative

HORIZON CORE administre et gouverne l'écosystème des systèmes
d'orchestration. Il ne remplace pas leurs orchestrateurs et ne prend pas
en charge leur gestion opérationnelle quotidienne.

La gestion administrative centrale doit rester **générique, stable et
commune** à des systèmes d'orchestration pouvant intervenir dans des
domaines très différents.

La règle de séparation est la suivante :

-   HORIZON CORE conserve les informations administratives communes
    nécessaires pour identifier, référencer, superviser et gouverner les
    systèmes.
-   Chaque système d'orchestration conserve la responsabilité de ses
    données métier, de ses ressources et de son fonctionnement
    opérationnel.
-   HORIZON CORE ne centralise pas les contenus métier par simple
    commodité administrative.
-   Les informations administratives centrales doivent permettre de
    retrouver les références utiles sans imposer aux systèmes une
    structure opérationnelle uniforme.

## 4. Catégories de données administratives

Le périmètre administratif couvre les catégories suivantes. Cette liste
définit le domaine de gouvernance ; elle ne constitue pas une
prescription de tables ou de schémas physiques.

### 4.1 Identité et référencement des systèmes

Informations permettant d'identifier un système d'orchestration dans
l'écosystème : - identifiant stable et nom de référence ; - description
et domaine d'activité ; - état administratif et historique de cet état
; - plateforme ou environnement de rattachement ; - référence de son
orchestrateur responsable ; - références documentaires et techniques
utiles ; - dates d'enregistrement et de mise à jour.

L'enregistrement central ne prouve pas que le système est techniquement
accessible, fonctionnel, actif ou conforme. Ces états doivent être
établis séparément par des vérifications documentées.

### 4.2 Identités et responsabilités

Informations permettant d'identifier les personnes et identités
techniques auxquelles sont attribuées des responsabilités
administratives : - identifiant de l'identité ; - nature humaine ou
technique ; - rôle et périmètre de responsabilité ; - rattachement
éventuel à un système ; - période de validité de l'affectation ; -
référence de l'autorité ayant accordé le rôle.

Les secrets d'authentification, clés privées, jetons et mots de passe ne
font jamais partie de ces données de registre.

### 4.3 Référencement administratif des projets

HORIZON CORE conserve les informations nécessaires pour connaître les
projets de l'écosystème et leurs rattachements : - identifiant central
et nom de référence ; - description administrative ; - système
d'orchestration responsable ; - systèmes contributeurs déclarés, le cas
échéant ; - responsables et périmètres de responsabilité ; - état
administratif ; - références vers les espaces de travail et sources
faisant autorité.

La fiche centrale ne remplace pas l'espace opérationnel du projet et ne
contient pas par défaut ses documents, livrables, données métier ou
historiques détaillés.

Un projet partagé demeure une seule unité métier. La contribution d'un
autre système ne transfère pas automatiquement la responsabilité globale
du projet.

### 4.4 Relations entre systèmes et projets

Les relations administratives permettent à HORIZON CORE de comprendre
: - quel orchestrateur est responsable de chaque système ; - quels
projets sont administrés par chaque système ; - quel système est
responsable d'un projet ; - quels systèmes contribuent à un projet
partagé ; - quelles relations de dépendance, d'interface ou de
collaboration ont été déclarées et validées.

Une relation enregistrée ne constitue pas une permission d'accès. Les
droits d'accès sont accordés par une décision distincte, limitée et
révocable.

### 4.5 Configuration administrative centrale

Les paramètres centraux comprennent uniquement les éléments génériques
nécessaires à l'administration de HORIZON CORE : référentiels communs,
règles de nommage et d'identification, paramètres administratifs
transversaux et références aux politiques applicables.

Les configurations internes des agents, outils, workflows et services
opérationnels restent sous la responsabilité du système concerné.

Les secrets et credentials doivent être conservés dans un mécanisme
sécurisé dédié, distinct du registre administratif et des documents de
gouvernance.

### 4.6 Gouvernance et décisions

Les données de gouvernance comprennent les politiques et leurs versions,
demandes, autorisations, refus, révocations, arbitrages, validations et
évaluations administratives.

Toute décision doit être rattachée à une autorité identifiable, à un
objet, à un périmètre, à une justification et à une période de validité.

### 4.7 Traçabilité administrative

Les événements administratifs significatifs sont conservés afin de
pouvoir reconstituer les changements de responsabilité, de statut, de
rattachement, de configuration et d'autorisation.

Les journaux administratifs sont distincts des journaux techniques et
opérationnels produits par les systèmes d'orchestration.

## 5. Autorité et responsabilités

### 5.1 HORIZON CORE

HORIZON CORE est l'autorité centrale de gouvernance administrative de
l'écosystème. Dans les limites des pouvoirs qui lui sont attribués, il
: - maintient le référentiel administratif central ; - veille à
l'identification des systèmes et de leurs responsables ; - supervise les
rattachements administratifs des projets ; - examine et décide les
demandes de collaboration et d'accès inter-systèmes ; - conserve les
décisions et leur historique ; - signale les informations manquantes,
incohérentes ou non vérifiées ; - arbitre les conflits de gouvernance
qui relèvent de son autorité.

Cette autorité centrale ne signifie pas que HORIZON CORE exécute les
opérations des systèmes ou devient propriétaire de leurs données métier.

### 5.2 Orchestrateur responsable d'un système

L'orchestrateur est responsable de la fiabilité des informations
administratives qu'il transmet à HORIZON CORE concernant son système et
ses projets : identité, responsables, rattachements, contributeurs,
statuts déclarés et changements pertinents.

Il reste responsable de la gestion opérationnelle de son environnement.

### 5.3 Responsables de projet et systèmes contributeurs

Le responsable du projet et les systèmes contributeurs fournissent les
informations nécessaires à l'exactitude des rattachements, des
responsabilités et des références documentaires. La contribution ne
confère aucun droit administratif ou technique non explicitement
accordé.

### 5.4 Utilisateurs et identités techniques

Toute action administrative doit être effectuée par une identité
reconnue et autorisée. Les actions sensibles doivent être attribuables à
une autorité et faire l'objet d'une trace vérifiable.

## 6. Règles d'identification et de qualité

1.  Chaque système, projet, identité, relation et décision
    administrative possède un identifiant stable.
2.  Les noms affichés peuvent évoluer ; les identifiants ne doivent pas
    dépendre de ces noms.
3.  Les notions de système d'orchestration, orchestrateur et projet
    restent distinctes.
4.  Un système intégré doit avoir un responsable identifié. À défaut,
    son dossier est signalé comme incomplet et son état ne peut être
    présenté comme pleinement validé.
5.  Chaque projet possède un système responsable clairement désigné.
6.  Les contributeurs éventuels sont enregistrés séparément du système
    responsable.
7.  Les statuts « enregistré », « évalué », « accessible », «
    fonctionnel », « actif » et « conforme » ne sont pas
    interchangeables.
8.  Toute donnée administrative déclarative doit pouvoir être distinguée
    d'une donnée vérifiée, avec sa source et sa date de vérification
    lorsque cela est pertinent.
9.  Les références vers les ressources doivent désigner la source
    faisant autorité ou préciser qu'il s'agit d'une copie, d'un export
    ou d'un miroir.
10. Les doublons et incohérences sont signalés et résolus sans fusion
    automatique susceptible de perdre la provenance.

## 7. Accès, autorisations et séparation

Les accès aux données administratives sont accordés selon le besoin d'en
connaître et le principe du moindre privilège.

Les règles suivantes sont obligatoires : - aucun accès inter-systèmes
n'est ouvert par défaut ; - une relation de dépendance ou de
collaboration ne crée pas de droit d'accès ; - toute autorisation
précise le demandeur, l'autorité décisionnaire, la finalité, les
ressources ou métadonnées concernées, le périmètre, les conditions et la
durée ou le critère de fin ; - les autorisations sont révocables et leur
révocation est tracée ; - les droits sont réexaminés lorsque les
responsabilités ou les relations changent ; - les permissions doivent
être appliquées par les mécanismes techniques des plateformes.

Les données administratives ne sont pas toutes publiques au sein de
l'écosystème. Les informations relatives aux identités, responsabilités,
décisions, configurations et contrôles d'accès doivent être protégées
selon leur sensibilité.

## 8. Classification et minimisation

La classification administrative utilise le référentiel commun défini
par la politique générale : Public, Interne, Confidentiel et Hautement
sensible.

La classification dépend de la nature de l'information et du risque lié
à sa divulgation, sa modification, son indisponibilité ou son
utilisation non autorisée.

La présente politique n'ajoute pas de nouvelle échelle de
classification. Une métadonnée de domaine administratif peut préciser la
nature de l'information sans remplacer le niveau de sensibilité.

HORIZON CORE ne conserve que les données nécessaires à l'identification,
l'administration, la gouvernance, la supervision et la traçabilité. Les
informations personnelles non nécessaires et les contenus opérationnels
détaillés sont exclus du registre central.

## 9. Cycle de vie des données administratives

Le cycle de vie comprend : 1. création ou réception ; 2. vérification et
qualification ; 3. enregistrement dans le référentiel approprié ; 4.
mise à jour contrôlée ; 5. consultation et utilisation selon les droits
; 6. archivage lorsque l'information n'est plus active mais doit être
conservée ; 7. rectification, clôture ou suppression autorisée.

Une modification de responsable, de rattachement ou de statut ne doit
pas effacer l'état précédent. L'historique nécessaire à la compréhension
des décisions est préservé.

La suppression d'un système ou d'un projet du registre ne doit pas
entraîner automatiquement la suppression de ses données opérationnelles
ni des preuves administratives qui doivent être conservées.

Les durées précises de conservation ne sont pas fixées par cette
politique. Elles doivent être définies en cohérence avec la politique
générale, les finalités, les obligations applicables et les besoins de
preuve.

## 10. Journalisation et auditabilité

Doivent être tracés au minimum : - création et modification des fiches
systèmes et projets ; - changement de responsable ou de contributeur ; -
changement de statut ; - création ou modification d'une relation ; -
demande, attribution, modification et révocation d'un droit ; - décision
de gouvernance ou d'arbitrage ; - modification des paramètres centraux
; - archivage, clôture et suppression autorisée.

Chaque événement conserve, lorsque cela est applicable : identifiant,
date et heure, auteur, action, objet concerné, résultat, motif ou
référence de décision et valeurs modifiées non sensibles.

Les journaux ne doivent pas contenir de secrets. Leur intégrité, leur
accès et leur durée de conservation doivent être définis dans la
conception technique.

## 11. Déclinaison sur les plateformes

La présente politique fixe les responsabilités et les règles ; elle ne
présume pas de la structure physique déjà déployée.

-   **Supabase / PostgreSQL :** support candidat pour le registre
    administratif structuré, les identifiants, les rattachements, les
    relations, les rôles, les autorisations, les décisions et les
    événements administratifs, sous réserve de l'audit et de la
    validation de l'architecture.
-   **GitHub :** gestion versionnée du code backend, des schémas,
    migrations validées, contrats d'interface et documents de
    gouvernance techniques. Les secrets sont interdits dans le dépôt et
    son historique.
-   **Google Drive :** conservation des documents de référence, pièces
    justificatives et rapports administratifs, avec contrôle des droits
    effectifs et identification des sources faisant autorité.

Les supports ne doivent pas devenir des sources concurrentes. Chaque
type d'information doit avoir une source faisant autorité clairement
identifiée. Les copies éventuelles sont signalées et ne doivent pas être
modifiées indépendamment de la source.

## 12. Exigences pour le backend administratif

Le backend administratif devra permettre, après audit et validation de
la cible : - l'enregistrement et la consultation des systèmes
d'orchestration ; - la gestion de leurs fiches administratives et
responsables ; - le référencement administratif des projets et de leurs
rattachements ; - la déclaration des systèmes contributeurs et des
relations ; - la gestion des identités, rôles et périmètres
d'autorisation ; - le traitement des demandes et décisions de
gouvernance ; - la gestion des statuts et paramètres administratifs
communs ; - la consultation de l'historique et des événements
administratifs.

Ces exigences ne prescrivent ni tables, ni colonnes, ni endpoints, ni
mécanisme physique précis. Le modèle technique doit être dérivé de
l'architecture existante et validé avant toute migration ou modification
du backend.

## 13. Contrôle et évolution de la politique

Toute évolution de la présente politique doit : - être motivée par un
besoin administratif démontré ; - être cohérente avec la politique
générale ; - préserver la séparation entre données administratives et
opérationnelles ; - être versionnée et approuvée par l'autorité
compétente ; - conserver la traçabilité des changements.

Une recommandation issue d'une veille, d'un agent ou d'un système
externe ne modifie pas automatiquement la politique.

## 14. Points à valider avant mise en œuvre

Restent à examiner à partir de l'architecture réelle : - l'emplacement
et la source faisant autorité pour chaque catégorie administrative ; -
l'articulation avec l'authentification et les permissions déjà présentes
; - la structure du registre central dans Supabase ; - les règles
techniques d'accès et de séparation ; - les modalités de journalisation
et de conservation ; - les interfaces administratives entre HORIZON CORE
et les orchestrateurs.

Aucune table, migration, permission ou modification backend n'est
autorisée par la seule publication de cette politique.

**Principe directeur : la gouvernance administrative centrale doit être
commune à tous les systèmes d'orchestration, tandis que leur
organisation et leurs données opérationnelles restent autonomes.**
