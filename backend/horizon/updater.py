"""Mise a jour de l'installation HORIZON (bouton « Mettre a jour »).

Une seule action, deux environnements :

- installation **locale** (le moteur tourne sur le meme PC que le code) :
  recuperation du code (`git pull`) puis recompilation de l'interface servie
  (`npm run build`) ;
- **serveur en ligne** : declenchement de la chaine GitHub existante
  (`workflow_dispatch` sur `deploy-app.yml`), qui construit l'interface, la
  deploie et redemarre le service.

Aucune valeur de secret n'est journalisee ni renvoyee. Le declenchement exige le
role administrateur (controle dans la route).
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

#: Racine du projet : backend/horizon/updater.py -> backend -> racine.
ROOT = Path(__file__).resolve().parents[2]
BRANCH = "main"
WORKFLOW_FILE = "deploy-app.yml"
MAX_LOG = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mode() -> str:
    """Environnement de mise a jour : local, server ou off (jamais devinne).

    Convention honnete du projet : le poste de l'utilisateur est sous Windows
    (installation locale) ; le serveur en ligne est sous Linux. Un reglage
    explicite `HORIZON_UPDATE_MODE` reste prioritaire.
    """
    forced = (os.getenv("HORIZON_UPDATE_MODE") or "").strip().lower()
    if forced in {"local", "server", "off"}:
        return forced
    if not (ROOT / ".git").exists():
        return "off"
    if os.name == "nt":
        return "local" if shutil.which("npm") else "off"
    return "server"


_STATE: dict = {
    "state": "idle",  # idle | running | done | error
    "mode": None,
    "started_at": None,
    "finished_at": None,
    "detail": "",
    "log": [],
}
_LOCK = threading.Lock()


def _append(line: str) -> None:
    with _LOCK:
        _STATE["log"].append(f"{_now()}  {line}")
        if len(_STATE["log"]) > MAX_LOG:
            del _STATE["log"][: len(_STATE["log"]) - MAX_LOG]


def status() -> dict:
    """Etat courant, non sensible, lisible par l'interface."""
    mode = _mode()
    with _LOCK:
        snapshot = dict(_STATE)
        snapshot["log"] = list(_STATE["log"])
    snapshot["mode"] = mode
    snapshot["available"] = mode != "off"
    snapshot["branch"] = BRANCH
    snapshot["repo_root"] = str(ROOT) if mode == "local" else None
    return snapshot


def _run(cmd: list[str], cwd: Path) -> int:
    _append("$ " + " ".join(cmd))
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    except OSError as exc:  # binaire absent
        _append(f"erreur : {exc}")
        return 1
    for line in (proc.stdout or "").strip().splitlines()[-12:]:
        _append(line)
    for line in (proc.stderr or "").strip().splitlines()[-12:]:
        _append(line)
    return proc.returncode


def _fail(detail: str) -> None:
    with _LOCK:
        _STATE.update(state="error", detail=detail, finished_at=_now())


def _done(detail: str) -> None:
    with _LOCK:
        _STATE.update(state="done", detail=detail, finished_at=_now())


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True
    ).stdout.strip()


def _run_local() -> None:
    """Installation locale : recuperation du code puis recompilation."""
    if not (ROOT / ".git").exists():
        _fail("Cette copie n'est pas un depot Git : mise a jour impossible.")
        return
    before = _head()
    if _run(["git", "fetch", "--quiet", "origin"], ROOT) != 0:
        _fail("Connexion a GitHub impossible (pas d'acces reseau ?).")
        return
    if _run(["git", "pull", "--ff-only", "--quiet", "origin", BRANCH], ROOT) != 0:
        _fail("git pull refuse (modifications locales ou divergence).")
        return
    after = _head()
    if before == after:
        _done("Deja a jour : aucun nouveau code.")
        return
    _append(f"nouveau code : {before[:7]} -> {after[:7]}")
    lock_changed = subprocess.run(
        ["git", "diff", "--name-only", before, after, "--", "package-lock.json"],
        cwd=str(ROOT), capture_output=True, text=True,
    ).stdout.strip()
    if lock_changed and _run(["npm", "ci"], ROOT) != 0:
        _fail("Echec de l'installation des dependances (npm ci).")
        return
    if _run(["npm", "run", "build"], ROOT) != 0:
        _fail("Echec de la compilation de l'interface.")
        return
    _done("Mise a jour locale terminee. Rechargez la fenetre (Ctrl+F5).")


def _run_server() -> None:
    """Serveur en ligne : mise a jour du depot puis redemarrage du service.

    Execute de facon **detachee** : la reponse part avant le redemarrage, sans
    quoi le service se couperait en pleine requete. L'interface est recompilee si
    `npm` est present ; sinon elle reste fournie par la chaine GitHub.
    """
    root = shlex.quote(str(ROOT))
    script = (
        f"cd {root} && git fetch --quiet origin && git reset --hard --quiet origin/{BRANCH} ; "
        ".venv/bin/pip install -q -r backend/requirements.txt ; "
        "( if command -v npm >/dev/null 2>&1; then npm ci --silent && npm run build --silent; "
        "else echo 'npm absent : interface fournie par la chaine GitHub'; fi ) ; "
        "sleep 2 ; systemctl restart horizon"
    )
    _append("mise a jour serveur : git fetch/reset + redemarrage (detache)")
    try:
        subprocess.Popen(
            ["bash", "-lc", script],
            cwd=str(ROOT),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        _fail(f"Lancement de la mise a jour impossible : {exc}")
        return
    _done("Mise a jour en ligne lancee. Le service redemarrera dans ~15 secondes ; rechargez alors la page.")


def start() -> dict:
    """Lance la mise a jour en tache de fond et renvoie l'etat immediat."""
    mode = _mode()
    with _LOCK:
        if _STATE["state"] == "running":
            snapshot = dict(_STATE)
            snapshot["log"] = list(_STATE["log"])
            snapshot["mode"] = mode
            snapshot["available"] = mode != "off"
            return snapshot
    if mode == "off":
        _fail("Mise a jour non disponible dans cet environnement.")
        return status()
    with _LOCK:
        _STATE.update(
            state="running", mode=mode, started_at=_now(), finished_at=None,
            detail="Mise a jour en cours...", log=[],
        )
    target = _run_local if mode == "local" else _run_server
    threading.Thread(target=target, name="horizon-update", daemon=True).start()
    return status()

