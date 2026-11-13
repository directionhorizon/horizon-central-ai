# HORIZON Core API — première base locale

Cette API implémente la santé du service, le registre de capacités et la persistance SQLite des sessions/messages. Elle n'appelle volontairement aucun LLM : un message est enregistré avec le statut `accepted_no_model` tant que le LLM Manager n'est pas raccordé.

## Démarrage Windows (PowerShell)

```powershell
cd "C:\Users\hp\HORIZON LOCAL AI\02 CODE ET ARCHITECTURE TECHNIQUE\02_CODE_SOURCE\HORIZON_APP\backend"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Documentation interactive : `http://127.0.0.1:8000/docs`.

La commande suppose que le projet sera placé à l'emplacement local cible indiqué dans le référentiel ; ne pas la lancer avant le placement définitif. Ne jamais versionner `.env`, `.venv` ou `data/`.
