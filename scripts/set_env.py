"""Ecrit ou met a jour des variables dans un fichier .env, sans jamais afficher les valeurs.

Usage :
    python scripts/set_env.py <chemin_env> <json_base64>

`json_base64` est un objet JSON {NOM_VARIABLE: valeur} encode en base64. Les valeurs
vides sont ignorees (une variable deja presente n'est donc jamais effacee par un secret
non renseigne). Aucune valeur n'est imprimee : seuls les NOMS mis a jour le sont.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path


def upsert(path: Path, values: dict[str, str]) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    updated: list[str] = []
    for key, raw in values.items():
        value = str(raw or "").strip()
        if not value:
            continue
        prefix = f"{key}="
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                lines[index] = f"{key}={value}"
                break
        else:
            lines.append(f"{key}={value}")
        updated.append(key)
    if not lines:
        return updated
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return updated


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: set_env.py <env_path> <json_base64>")
        return 2
    path = Path(argv[1])
    try:
        payload = json.loads(base64.b64decode(argv[2]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        print("payload invalide")
        return 2
    if not isinstance(payload, dict):
        print("payload invalide (objet attendu)")
        return 2
    updated = upsert(path, {str(k): str(v) for k, v in payload.items()})
    print("Variables mises a jour : " + (", ".join(updated) if updated else "aucune"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
