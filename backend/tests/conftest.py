"""Fixtures partagées des tests backend.

La base de test est toujours temporaire : les tests ne doivent jamais toucher
`backend/data/horizon.db`, qui contient les données réelles de l'utilisateur.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="horizon-tests-"))
os.environ["HORIZON_DATABASE_PATH"] = str(TEST_DB_DIR / "horizon-test.db")
os.environ["HORIZON_WORKSPACE_DIR"] = str(TEST_DB_DIR / "workspace")
for variable in (
    "HORIZON_ADMIN_TOKEN",
    "HORIZON_GOOGLE_CLIENT_ID",
    "HORIZON_SUPABASE_URL",
    "HORIZON_SUPABASE_KEY",
    "HORIZON_SYNC_AUTO",
):
    os.environ.pop(variable, None)

import pytest  # noqa: E402  (l'environnement doit être fixé avant les imports applicatifs)
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def horizon_app():
    import app as app_module

    return app_module


@pytest.fixture()
def client(horizon_app):
    # Origine locale explicite : le garde-fou réseau refuse tout autre hôte
    # lorsqu'aucune authentification n'est configurée.
    with TestClient(horizon_app.app, base_url="http://127.0.0.1:8000") as test_client:
        yield test_client
