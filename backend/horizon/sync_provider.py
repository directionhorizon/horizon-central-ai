"""Adaptateur de synchronisation distante (fournisseur-agnostique).

Implémentation par défaut : Supabase via son API REST (PostgREST).
Aucune clé n'est écrite en base ni renvoyée : seul le nom de la variable
d'environnement est référencé côté application, la valeur reste dans `.env`.

Si les variables ne sont pas définies, `get_provider()` renvoie `None` :
HORIZON continue de fonctionner hors ligne, la file d'attente est conservée.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

TIMEOUT_S = 20.0


class SyncError(RuntimeError):
    """Erreur de synchronisation distante, message non sensible."""


class SyncProvider:
    name = "unknown"

    @property
    def configured(self) -> bool:  # pragma: no cover - surcharge
        return False

    def push(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
        raise SyncError("Fournisseur non configuré.")

    def pull(self, table: str, since: str | None = None) -> list[dict[str, Any]]:  # pragma: no cover
        raise SyncError("Fournisseur non configuré.")

    def update(self, table: str, entity_id: str, payload: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
        raise SyncError("Fournisseur non configuré.")

    def delete(self, table: str, entity_id: str) -> dict[str, Any]:  # pragma: no cover
        raise SyncError("Fournisseur non configuré.")


class SupabaseProvider(SyncProvider):
    name = "supabase"

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self._base_url and self._api_key)

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def push(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/rest/v1/{table}"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=self._headers(prefer="resolution=merge-duplicates,return=representation"),
                timeout=TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            raise SyncError(f"Échec réseau : {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise SyncError(f"HTTP {response.status_code} sur {table}")
        try:
            data = response.json()
        except ValueError:
            return {}
        if isinstance(data, list):
            return data[0] if data else {}
        return data if isinstance(data, dict) else {}

    def update(self, table: str, entity_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Met à jour une ligne existante (PATCH filtré par id).

        Un PATCH n'essaie jamais d'insérer : il ne peut donc pas échouer sur
        des colonnes obligatoires absentes, contrairement à un upsert.
        """
        url = f"{self._base_url}/rest/v1/{table}"
        body = {key: value for key, value in payload.items() if key != "id"}
        try:
            response = httpx.patch(
                url,
                params={"id": f"eq.{entity_id}"},
                json=body,
                headers=self._headers(prefer="return=representation"),
                timeout=TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            raise SyncError(f"Échec réseau : {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise SyncError(f"HTTP {response.status_code} sur {table}")
        try:
            data = response.json()
        except ValueError:
            return {}
        if isinstance(data, list):
            return data[0] if data else {}
        return data if isinstance(data, dict) else {}

    def delete(self, table: str, entity_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/rest/v1/{table}"
        try:
            response = httpx.delete(
                url,
                params={"id": f"eq.{entity_id}"},
                headers=self._headers(),
                timeout=TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            raise SyncError(f"Échec réseau : {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise SyncError(f"HTTP {response.status_code} sur {table}")
        return {}

    def pull(self, table: str, since: str | None = None) -> list[dict[str, Any]]:
        url = f"{self._base_url}/rest/v1/{table}"
        params: dict[str, str] = {"select": "*", "limit": "500"}
        if since:
            params["updated_at"] = f"gt.{since}"
        try:
            response = httpx.get(url, params=params, headers=self._headers(), timeout=TIMEOUT_S)
        except httpx.HTTPError as exc:
            raise SyncError(f"Échec réseau : {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise SyncError(f"HTTP {response.status_code} sur {table}")
        try:
            data = response.json()
        except ValueError:
            return []
        return data if isinstance(data, list) else []


def get_provider() -> SyncProvider | None:
    """Renvoie le fournisseur distant si réellement configuré, sinon `None`."""
    base_url = os.getenv("HORIZON_SUPABASE_URL", "").strip()
    api_key = os.getenv("HORIZON_SUPABASE_KEY", "").strip()
    if base_url and api_key:
        return SupabaseProvider(base_url, api_key)
    return None


def provider_status() -> dict[str, Any]:
    """État non sensible du fournisseur, exposé à l'interface."""
    provider = get_provider()
    if provider is None:
        return {
            "configured": False,
            "provider": "none",
            "required_env": ["HORIZON_SUPABASE_URL", "HORIZON_SUPABASE_KEY"],
        }
    return {"configured": True, "provider": provider.name, "required_env": []}
