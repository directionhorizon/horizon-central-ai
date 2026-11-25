"""Registre des fournisseurs de paiement.

Aucun fournisseur n'est imposé : le registre est ouvert. Ajouter un moyen de
paiement = déposer un adaptateur qui respecte `PaymentProvider`, puis
l'enregistrer ici. Le routeur, la page et le moteur natif n'ont pas à changer.

Un fournisseur est « configuré » quand toutes ses variables d'environnement
sont présentes. Sans configuration, l'adaptateur refuse honnêtement : aucun
résultat n'est fabriqué.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Mapping

from .base import (
    MODE_CHECKOUT,
    MODE_INTENT,
    MODE_SETUP,
    PaymentProvider,
    PaymentRequest,
    PaymentResult,
    ProviderError,
)
from .mollie_provider import MollieProvider
from .moneyfusion_provider import MoneyFusionProvider
from .paypal_provider import PayPalProvider
from .stripe_provider import StripeProvider

_REGISTRY: dict[str, PaymentProvider] = {}


def register(provider: PaymentProvider) -> PaymentProvider:
    """Enregistre un adaptateur (idempotent sur `kind`)."""
    if not provider.kind:
        raise ProviderError("Un adaptateur de paiement doit déclarer un `kind`.")
    _REGISTRY[provider.kind] = provider
    return provider


def get_provider(kind: str) -> PaymentProvider:
    key = str(kind or "").strip().lower()
    provider = _REGISTRY.get(key)
    if provider is None:
        known = ", ".join(sorted(_REGISTRY)) or "aucun"
        raise ProviderError(
            f"Fournisseur de paiement « {kind} » inconnu (disponibles : {known})."
        )
    return provider


def providers() -> list[PaymentProvider]:
    return [_REGISTRY[key] for key in sorted(_REGISTRY)]


def default_provider() -> str:
    """Fournisseur par défaut, choisi par configuration (jamais codé en dur)."""
    return (os.getenv("HORIZON_PAYMENT_PROVIDER") or "stripe").strip().lower()


def _env_reader(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _is_configured(provider: PaymentProvider, env_reader: Callable[[str], str]) -> bool:
    return all(env_reader(name) for name in provider.env_vars)


def describe_providers(
    env_reader: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    """Liste des fournisseurs avec leur état de configuration (sans secret)."""
    read = env_reader or _env_reader
    default = default_provider()
    items = []
    for provider in providers():
        item = provider.describe(configured=_is_configured(provider, read))
        item["default"] = provider.kind == default
        items.append(item)
    return items


def sync_registry(db: Any) -> list[dict[str, Any]]:
    """Enregistre ou rafraîchit une fiche par fournisseur dans le registre.

    Une fiche = un identifiant stable (`payment:<kind>`), jamais de doublon.
    Aucun secret n'est écrit : seul le *nom* de la variable d'environnement est
    conservé. Le statut reste « partiel » tant qu'un test réel n'a pas été
    déclenché depuis la page des connexions (règle du registre).
    """
    from ..repositories import integrations as integrations_repo

    fiches: list[dict[str, Any]] = []
    for provider in providers():
        configured = _is_configured(provider, _env_reader)
        fiches.append(
            integrations_repo.upsert_integration(
                db,
                f"payment:{provider.kind}",
                {
                    "name": provider.label or provider.kind,
                    "category": "payment",
                    "method": "api_key" if provider.env_vars else "endpoint",
                    "endpoint": provider.docs_url,
                    "status": "partial" if configured else "not_configured",
                    "capabilities": ", ".join(provider.capabilities),
                    "api_key_env": provider.env_vars[0] if provider.env_vars else "",
                },
            )
        )
    return fiches


def resolve_credentials(
    provider: PaymentProvider,
    *,
    account: str | None = None,
    credential_reader: Callable[[str | None, str, str], str] | None = None,
    env_reader: Callable[[str], str] | None = None,
) -> dict[str, str]:
    """Résout les secrets d'un fournisseur, sans jamais les journaliser.

    - adaptateur à une seule variable : la fiche d'intégration (`account`) peut
      désigner le nom de variable à utiliser ;
    - adaptateur à plusieurs variables : chaque variable déclarée est lue dans
      l'environnement (la fiche d'intégration sert alors de repère humain).
    """
    read_env = env_reader or _env_reader
    account = str(account or "").strip()
    if account and len(provider.env_vars) == 1 and credential_reader is not None:
        name = provider.env_vars[0]
        return {name: credential_reader(account, name, provider.label)}
    return {name: read_env(name) for name in provider.env_vars}


register(StripeProvider())
register(PayPalProvider())
register(MollieProvider())
register(MoneyFusionProvider())

__all__ = [
    "MODE_CHECKOUT",
    "MODE_INTENT",
    "MODE_SETUP",
    "PaymentProvider",
    "PaymentRequest",
    "PaymentResult",
    "ProviderError",
    "default_provider",
    "describe_providers",
    "get_provider",
    "providers",
    "register",
    "resolve_credentials",
    "sync_registry",
]
