# HORIZON LOCAL AI — Contrat API du cœur (proposition v0.1)

**Statut :** contrat de travail, non connecté à un serveur.  
**But :** fixer les frontières entre l'application React, le cœur HORIZON, le LLM Manager et les services de mémoire avant d'implémenter les connexions.

## 1. Principes non négociables

- Windows reste l'environnement principal d'exécution.
- GitHub privé reste la référence du code et de la documentation versionnée.
- Google Drive reste l'espace de mémoire persistante et de continuité des projets.
- Le cœur HORIZON coordonne les fonctions communes ; il ne remplace pas les systèmes spécialisés externes.
- Le LLM Manager choisit un modèle selon la tâche/session, accepte une sélection manuelle et prévoit le fallback. La politique de routage appartient à HORIZON, pas au fournisseur.
- Les fournisseurs sont raccordés via un adaptateur commun compatible OpenAI lorsque possible. Aucun fournisseur n'est considéré disponible avant un test réel.
- Les opérations sensibles nécessitent une autorisation explicite conformément au référentiel de sécurité.

## 2. Frontières des composants

| Composant | Responsabilité | Ne doit pas faire |
|---|---|---|
| React UI (six espaces) | Présentation, saisie, affichage de l'état et des résultats | Accéder directement aux clés API ou décider seule du routage LLM |
| HORIZON Core API | Sessions, messages, orchestration fonctionnelle, politiques, autorisations | Être couplé à un fournisseur unique |
| LLM Manager | Résolution du modèle, exécution, timeout, fallback et traces de routage | Stocker les secrets dans le navigateur |
| Memory Service | Mémoire locale et connecteur Google Drive, provenance et synchronisation | Confondre GitHub avec la mémoire utilisateur |
| Tools/Integrations | Adaptateurs d'outils et services externes | Exécuter une action sensible sans contrôle d'autorisation |
| System Monitor | Collecte de métriques réelles depuis des sondes locales autorisées | Présenter des exemples comme des mesures réelles |

## 3. API proposée

Base locale : `/api/v1`.

| Méthode | Route | Usage |
|---|---|---|
| GET | `/health` (implémentée sous `/api/v1/health`) | Santé du service (sans révéler de secret) |
| GET | `/capabilities` (implémentée sous `/api/v1/capabilities`) | Capacités réellement activées et état des connecteurs |
| POST | `/sessions` | Créer une session |
| GET | `/sessions` | Lister les sessions |
| GET | `/sessions/{session_id}` | Lire une session et ses messages |
| POST | `/sessions/{session_id}/messages` | Envoyer un message et demander une réponse du cœur |
| POST | `/sessions/{session_id}/reset` | Réinitialiser une session après confirmation UI |
| GET | `/models` | Lister les modèles configurés et leur état de vérification |
| PUT | `/settings/model-selection` | Définir sélection auto/manuelle et modèle préféré |
| GET | `/memory/status` | État de la mémoire locale et du connecteur Drive |
| POST | `/memory/search` | Rechercher dans la mémoire autorisée |
| GET | `/system/metrics` | Mesures locales datées et source identifiée |
| GET | `/integrations` | État des intégrations et permissions accordées |

Les routes ci-dessus sont un contrat cible ; elles ne sont pas réputées implémentées dans cette archive.

## 4. Schémas d'échange

### Message entrant

```json
{
  "content": "Texte utilisateur",
  "attachments": [],
  "model_preference": { "mode": "auto", "provider_id": null, "model_id": null },
  "client_message_id": "uuid"
}
```

### Réponse du cœur

```json
{
  "session_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "Réponse",
    "created_at": "2026-01-01T12:00:00Z"
  },
  "execution": {
    "status": "completed",
    "provider_id": "provider-id",
    "model_id": "model-id",
    "fallback_used": false
  },
  "citations": [],
  "warnings": []
}
```

`provider_id` et `model_id` peuvent être absents si aucune exécution LLM n'a eu lieu. Ne jamais fabriquer une réponse assistant de succès lorsque le fournisseur échoue.

### Capacités

Chaque capacité doit annoncer un statut parmi `available`, `not_configured`, `unverified`, `degraded`, `unavailable`, avec une date de vérification et une explication non sensible. Les interfaces affichent ce statut plutôt que des badges de disponibilité statiques.

## 5. Session conversationnelle commune

Les deux vues Main Workbench et AI Control Center consomment le même `session_id` et le même flux de messages via un service partagé. Le stockage navigateur n'est qu'un cache provisoire. La persistance de référence doit être assurée par l'API du cœur et le stockage local Windows ; la synchronisation Google Drive est une fonction séparée et contrôlée.

## 6. Sécurité minimale

- Secrets uniquement côté serveur, dans une configuration locale protégée ou un gestionnaire de secrets.
- Ne jamais renvoyer les valeurs de secrets dans `/capabilities`, `/integrations` ou les logs.
- Valider taille/type des pièces jointes et chemins de fichiers.
- Contrôler les actions système par permission et confirmation.
- Journaliser l'identité de l'action, la cible, le résultat et l'horodatage, sans exposer de données sensibles.
- Les erreurs de fournisseur doivent être explicites et ne déclenchent un fallback que selon la politique configurée.

## 7. Critères d'acceptation avant connexion réelle

1. Une session créée dans une vue est visible dans l'autre.
2. Un message est persisté par le backend et survit au redémarrage du navigateur.
3. `/capabilities` distingue une intégration configurée d'une intégration réellement testée.
4. Le LLM Manager expose le modèle choisi, le fallback et l'erreur éventuelle.
5. Une panne fournisseur ne produit pas de réponse fictive.
6. Les données de démonstration sont clairement identifiées et désactivables.
7. Les opérations sensibles sont bloquées sans autorisation valide.
8. Les tests API, interface et sécurité sont documentés avant toute synchronisation de production.

## 8. État dans la version actuelle

- Les six vues React sont regroupées dans une seule application.
- Main Workbench et AI Control Center partagent un état de conversation côté client, avec persistance navigateur dans cette branche.
- Le backend, le routage LLM réel, Google Drive, GitHub, les agents, les outils et les métriques système ne sont pas connectés par ce contrat.
