"""Contrat commun des fournisseurs de paiement.

Un fournisseur (Stripe, PayPal, Mollie, autre) est un **adaptateur** : il reçoit
une demande normalisée et rend un résultat normalisé. Aucun fournisseur n'est
codé en dur dans le routeur ni dans la page : HORIZON reste le décideur.

Règles de sécurité :
- aucun numéro de carte, CVV ou donnée bancaire ne transite par HORIZON ;
- les secrets sont lus uniquement dans l'environnement (`api_key_env`) ;
- les erreurs remontées ne contiennent jamais de secret.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

#: Modes d'opération compris par les adaptateurs.
MODE_INTENT = "intent"      # intention de paiement (débit côté fournisseur)
MODE_CHECKOUT = "checkout"  # page de paiement hébergée (lien à ouvrir)
MODE_SETUP = "setup"        # enregistrement d'un moyen de paiement (sans débit)

#: Devises sans décimale : le montant est déjà en unité entière (FCFA, yen…).
#: Partagé par les adaptateurs pour éviter deux définitions divergentes.
ZERO_DECIMAL = frozenset(
    {
        "xof", "xaf", "jpy", "krw", "clp", "gnf", "cdf", "rwf", "bif", "mga", "kmf",
        "vnd", "pyg", "ugx", "djf", "isk",
    }
)


class ProviderError(RuntimeError):
    """Erreur d'un fournisseur de paiement, message lisible et sans secret."""


def fallback_detail(
    label: str, amount: int, currency: str, identifier: str = ""
) -> str:
    """Libellé lisible quand l'appelant n'a pas fourni de référence.

    Une ligne de paiement ne doit jamais rester vide : on y met le fournisseur,
    le montant et l'identifiant technique, sans jamais exposer de donnée bancaire.
    """
    text = f"Paiement {label} — {amount / 100:.2f} {str(currency or '').upper()}"
    if identifier:
        text += f" — {identifier}"
    return text


@dataclass(frozen=True)
class PaymentRequest:
    """Demande normalisée, indépendante du fournisseur."""

    amount: int
    currency: str = "eur"
    detail: str = ""
    customer_email: str = ""
    customer_name: str = ""
    success_url: str = ""
    cancel_url: str = ""
    customer: str = ""
    idempotency_key: str = ""

    def decimal_amount(self) -> str:
        """Montant en unité majeure, format « 10.00 » (PayPal, Mollie)."""
        return f"{self.amount / 100:.2f}"


@dataclass
class PaymentResult:
    """Résultat normalisé, quel que soit le fournisseur."""

    provider: str
    id: str
    status: str
    amount: int
    currency: str
    mode: str = MODE_INTENT
    detail: str = ""
    checkout_url: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "id": self.id,
            "status": self.status,
            "amount": self.amount,
            "currency": self.currency,
            "mode": self.mode,
            "detail": self.detail,
            "checkout_url": self.checkout_url,
        }


class PaymentProvider(ABC):
    """Adaptateur d'un fournisseur de paiement."""

    #: Identifiant technique stable (repris par l'API et la page).
    kind: str = ""
    #: Nom lisible affiché dans l'interface.
    label: str = ""
    #: Modes réellement supportés par l'adaptateur.
    capabilities: tuple[str, ...] = (MODE_INTENT,)
    #: Noms des variables d'environnement contenant les secrets.
    env_vars: tuple[str, ...] = ()
    #: Documentation publique du fournisseur.
    docs_url: str = ""

    @abstractmethod
    async def create(
        self,
        request: PaymentRequest,
        credentials: Mapping[str, str],
        mode: str = MODE_INTENT,
    ) -> PaymentResult:
        """Crée un paiement (ou un enregistrement de carte) chez le fournisseur."""

    async def refund(
        self,
        payment_id: str,
        amount: int,
        credentials: Mapping[str, str],
        reason: str = "",
    ) -> PaymentResult:
        """Rembourse un paiement. Refus honnête si l'adaptateur ne le gère pas."""
        raise ProviderError(
            f"Le fournisseur « {self.label} » ne gère pas encore les remboursements."
        )

    def verify_webhook(
        self, payload: bytes, headers: Mapping[str, str]
    ) -> dict[str, Any]:
        """Vérifie la signature d'un événement entrant. Refus par défaut."""
        raise ProviderError(
            f"Le fournisseur « {self.label} » n'a pas de vérification de webhook."
        )

    def webhook_event(self, event: Mapping[str, Any]) -> tuple[str, str] | None:
        """Traduit un événement vérifié en (identifiant de paiement, statut local)."""
        return None

    def describe(self, configured: bool = False) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "capabilities": list(self.capabilities),
            "env_vars": list(self.env_vars),
            "docs_url": self.docs_url,
            "configured": configured,
        }
