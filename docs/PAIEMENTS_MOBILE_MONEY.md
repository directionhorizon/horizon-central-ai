# HORIZON CENTRAL AI — Paiements et Mobile Money

**Statut :** adaptateur écrit, testé et enregistré au registre des connexions. Aucune clé réelle fournie à ce jour ; l'usage est différé.
**But :** fixer ce que la couche paiement de HORIZON fait, ce qu'elle ne fait pas, et pourquoi SasPay y occupe la place du **Mobile Money** pour l'Afrique centrale.

## 1. Deux couches à ne pas confondre

| Couche | Sens du flux | Source des données | État |
|---|---|---|---|
| **Suivi des flux** | observation | MAYELA CRM (Supabase, vues `horizon_feed_*`) | branché, lecture seule |
| **Paiement** | argent qui entre ou sort | fournisseurs (SasPay, Stripe…) | adaptateurs écrits, sans clé |

Le suivi des flux **n'utilise pas** SasPay. Les deux branches sont indépendantes.

## 2. Ce que la couche paiement fait, et ne fait pas

Elle fait :

- **encaisser** : un client paie, HORIZON reçoit une URL de paiement et suit le statut ;
- **décaisser** (selon le fournisseur) : envoyer de l'argent à un bénéficiaire.

Elle ne fait pas :

- payer Meta ou TikTok — aucune régie publicitaire ne s'acquitte par API ; le boost se paie par carte sur leur plateforme ;
- lire MAYELA ;
- décider seule : un paiement exige toujours `confirm=true`, c'est-à-dire une validation humaine explicite.

## 3. SasPay : la voie Mobile Money (Congo-Brazzaville)

Stripe, PayPal et les grands PSP ne couvrent pas le Congo. La réalité locale est le **Mobile Money** : MTN MoMo et Airtel Money, plus la carte pour le reste.

SasPay est une **couche d'intégration technique** (elle se définit elle-même comme ASPC, et précise n'être « ni un établissement de paiement, ni un agrégateur, ni un PSP, ni une banque »). Les fonds sont encaissés et conservés par des PSP agréés. Une seule API donne accès aux réseaux locaux.

Couverture déclarée pour le Congo (`cg`) : **MTN MoMo**, **Airtel Money**. Frais annoncés : **dès 4 %**, le taux le plus élevé de leur catalogue.

## 4. Implémenté / non implémenté

| Fonction | État |
|---|---|
| Encaissement par page hébergée (`POST /checkout-sessions/`) | implémenté |
| Vérification du webhook (signature HMAC + horodatage, tolérance 5 min) | implémenté |
| Traduction des événements (`transaction.success/failed/cancelled`) | implémenté |
| Idempotence des événements reçus | implémenté |
| Décaissement vers un numéro Mobile Money (`POST /payouts/initialize/`) | **non implémenté** (exige une IP whitelistée) |
| Remboursements | **non implémenté** — aucun endpoint public documenté ; l'adaptateur refuse honnêtement |

## 5. Configuration

Variables d'environnement (noms uniquement ; aucune valeur n'est versionnée) :

```
HORIZON_SASPAY_API_KEY          # sk_test_... (bac à sable) ou sk_live_...
HORIZON_SASPAY_WEBHOOK_SECRET   # affiché une seule fois à la création du webhook
HORIZON_SASPAY_BASE_URL         # vide = production ; sandbox-api.saspay.me/api/v1 = test
```

Webhook à déclarer côté SasPay (tableau de bord, jamais par API) :

```
https://horizon.mayela-crm.com/api/v1/payments/webhook/saspay
```

Événements à souscrire : `transaction.success`, `transaction.failed`, `transaction.cancelled`.

La fiche `payment:saspay` est créée automatiquement au démarrage du backend : catégorie `payment`, méthode `api_key`, capacités `checkout`. Elle passe de `not_configured` à `partial` dès que la variable existe, puis à `connected` après un test réel déclenché depuis la page Connexions.

## 6. Limite connue, non vérifiée

Le **rapprochement webhook → paiement local** n'est pas prouvé. SasPay transmet l'identifiant de la **transaction**, alors que HORIZON mémorise celui de la **session** de checkout. L'adaptateur transmet sa clé d'idempotence dans les métadonnées et la cherche en priorité dans l'événement, mais ce point doit être confirmé sur un vrai événement. En attendant, le statut peut être réconcilié à la demande avec `GET /checkout-sessions/{id}/status/`.

## 7. Sécurité

- Aucune donnée bancaire ne transite par HORIZON : le client paie chez le fournisseur.
- Les secrets vivent uniquement dans l'environnement ; les réponses de l'API ne contiennent que des **noms** de variables.
- Le webhook est rejeté si la signature **ou** l'horodatage est invalide — sans le contrôle d'âge, un événement intercepté resterait rejouable indéfiniment.
- Le KYC et le compte de versement appartiennent au titulaire du marchand, pas à l'exploitant technique.

## 8. Pourquoi c'est présent maintenant

La couche paiement est une **capacité préparée**, pas un besoin du jour : le suivi des campagnes passe par MAYELA, pas par SasPay. Elle est là pour que le jour où un encaissement devient nécessaire, l'intégration soit déjà écrite, testée et sans fournisseur imposé — conformément à la règle « aucun orchestrateur codé en dur ».
