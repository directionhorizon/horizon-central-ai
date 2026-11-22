"""Tests de la bibliothèque de skills et des signatures d'auteur.

Objectif : garantir que le catalogue est réellement cherchable et modifiable,
et que chaque écriture est signée côté serveur sans jamais exposer la
signature dans les réponses de l'API.
"""
from __future__ import annotations

from horizon.db import connect


def test_catalogue_de_depart_present(client):
    response = client.get("/api/v1/skills")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert "Recherche web" in names


def test_recherche_et_creation_de_skill(client):
    created = client.post(
        "/api/v1/skills",
        json={"name": "Veille concurrentielle", "category": "Recherche", "tags": "veille,marche"},
    )
    assert created.status_code == 201, created.text
    skill = created.json()

    trouve = client.get("/api/v1/skills", params={"q": "concurrentielle"})
    assert trouve.status_code == 200
    assert skill["id"] in {item["id"] for item in trouve.json()["items"]}

    par_categorie = client.get("/api/v1/skills", params={"category": "Recherche"})
    assert par_categorie.status_code == 200
    assert all(item["category"] == "Recherche" for item in par_categorie.json()["items"])


def test_associer_skill_a_un_systeme(client):
    system = client.post(
        "/api/v1/orchestrators", json={"name": "Systeme skill", "kind": "horizon"}
    ).json()
    skill = client.post("/api/v1/skills", json={"name": "Skill a associer"}).json()

    attached = client.post(
        f"/api/v1/orchestrators/{system['id']}/skills", json={"skill_id": skill["id"]}
    )
    assert attached.status_code == 200, attached.text
    assert skill["id"] in {item["id"] for item in attached.json()["skills"]}

    detached = client.delete(f"/api/v1/orchestrators/{system['id']}/skills/{skill['id']}")
    assert detached.status_code == 200
    assert skill["id"] not in {item["id"] for item in detached.json()["skills"]}


def test_import_bundle_securise(client):
    bundle = [
        {
            "id": "skill-importe-1",
            "name": "Compétence importée",
            "category": "Test",
            "description": "Provenance GitHub simulée.",
        }
    ]
    response = client.post("/api/v1/skills/import", json={"bundle": bundle, "origin": "github"})
    assert response.status_code == 200, response.text
    assert response.json()["created"] >= 1

    found = client.get("/api/v1/skills", params={"q": "importée"}).json()["items"]
    assert any(item["id"] == "skill-importe-1" for item in found)
    assert found[0]["origin"] == "github"


def test_import_paquet_sans_nom_refuse(client):
    response = client.post("/api/v1/skills/import", json={"source": "npm"})
    assert response.status_code == 400
    assert "paquet" in response.json()["detail"].lower()


def test_import_url_hote_non_autorise_refuse(client):
    response = client.post(
        "/api/v1/skills/import", json={"url": "https://exemple-malveillant.tld/skills.json"}
    )
    assert response.status_code == 400
    assert "non autorisée" in response.json()["detail"]


def test_sources_externes_proposees(client):
    response = client.get("/api/v1/skills/sources")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert {"github", "gitlab", "bitbucket", "huggingface", "openai", "anthropic", "npm", "pypi"} <= ids


def test_categories_nouvelles_peuplees(client):
    """Les nouvelles catégories métier contiennent au moins une compétence."""
    for category in (
        "Vente et relation client",
        "Support et opérations",
        "Données et BI",
        "Marketing et acquisition",
        "Automatisation et intégrations",
        "Sécurité et contrôle",
        "Formation et éducation",
    ):
        result = client.get("/api/v1/skills", params={"category": category}).json()
        assert result["count"] >= 1, f"catégorie vide : {category}"


def test_reclassement_des_competences_existantes(client):
    """Les compétences « métier » sont déplacées vers les nouvelles catégories."""
    finance = client.get("/api/v1/skills", params={"category": "Finance et comptabilité"}).json()
    assert finance["count"] >= 1
    juridique = client.get("/api/v1/skills", params={"category": "Juridique et conformité"}).json()
    assert juridique["count"] >= 1
    rh = client.get("/api/v1/skills", params={"category": "Ressources humaines"}).json()
    assert rh["count"] >= 1


def test_categories_et_outils_recommandes(client):
    response = client.get("/api/v1/skills/category-map")
    assert response.status_code == 200
    items = response.json()["items"]
    names = {item["category"] for item in items}
    assert "Vente et relation client" in names
    assert "Automatisation et intégrations" in names
    vente = next(item for item in items if item["category"] == "Vente et relation client")
    assert "tool-payment" in vente["tools"]


def test_detection_origine_par_hote():
    from horizon.routers.skills import _detect_origin

    assert _detect_origin("https://raw.githubusercontent.com/o/r/main/skills.json") == "github"
    assert _detect_origin("https://gist.githubusercontent.com/x/y/raw/skills.json") == "gist"
    assert _detect_origin("https://gitlab.com/o/r/-/raw/main/skills.json") == "gitlab"
    assert _detect_origin("https://bitbucket.org/o/r/raw/main/skills.json") == "bitbucket"
    assert _detect_origin("https://huggingface.co/datasets/x/skills.json") == "huggingface"
    assert _detect_origin("https://platform.openai.com/docs/skills.json") == "openai"
    assert _detect_origin("https://docs.anthropic.com/fr/skills.json") == "anthropic"


def test_ecriture_signee_mais_invisible(client):
    created = client.post("/api/v1/projects", json={"name": "Projet signe"})
    assert created.status_code == 201
    project = created.json()

    # La signature est bien stockée côté serveur...
    with connect() as db:
        rows = db.execute(
            "SELECT agent_auteur, systeme, provenance FROM authorship "
            "WHERE entity_type='project' AND entity_id=?",
            (project["id"],),
        ).fetchall()
    assert len(rows) >= 1
    assert rows[0]["systeme"] == "HORIZON CORE"

    # ... et jamais renvoyée par l'API.
    body = client.get(f"/api/v1/projects/{project['id']}").json()
    assert "authorship" not in body
    assert "agent_auteur" not in body
