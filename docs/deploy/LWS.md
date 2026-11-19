# Mise en ligne sur LWS — guide de déploiement

Guide générique et reproductible pour héberger HORIZON CENTRAL AI sur un **VPS LWS**
(Ubuntu/Debian). Remplacer `horizon.example.com` par votre domaine réel.

> Principe : le backend FastAPI sert **lui-même** l'interface compilée (`dist/`).
> Un seul processus suffit. Le backend n'écoute que sur `127.0.0.1` ; le TLS est
> assuré devant par un proxy (Caddy ou le proxy LWS).

## 0. Prérequis
- Un **VPS LWS** avec accès **SSH root**.
- Un **domaine** (ou sous-domaine) pointé vers l'IP du VPS (enregistrement `A`).
- Ports **80** et **443** ouverts.

## 1. Paquets et utilisateur
```bash
apt update && apt install -y python3 python3-venv git nodejs npm caddy
adduser --system --group --home /opt/horizon horizon
mkdir -p /var/lib/horizon && chown horizon:horizon /var/lib/horizon
```

## 2. Code (depuis GitHub)
```bash
sudo -u horizon git clone https://github.com/directionhorizon/horizon-central-ai.git /opt/horizon
cd /opt/horizon
sudo -u horizon python3 -m venv .venv
sudo -u horizon .venv/bin/pip install -r backend/requirements.txt
```

## 3. Interface compilée
```bash
cd /opt/horizon
npm ci
npm run build     # produit dist/, que le backend sert
```

## 4. Configuration serveur (backend/.env — jamais versionné)
```bash
TOKEN=$(cd /opt/horizon && .venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))")
cat > /opt/horizon/backend/.env <<EOF
HORIZON_ADMIN_TOKEN=$TOKEN
HORIZON_CORS_ORIGINS=https://horizon.example.com
HORIZON_DATABASE_PATH=/var/lib/horizon/horizon.db
# Online-first (Brique 2) — à renseigner ensuite, jamais dans le code :
HORIZON_SUPABASE_URL=
HORIZON_SUPABASE_KEY=
EOF
chown horizon:horizon /opt/horizon/backend/.env && chmod 600 /opt/horizon/backend/.env
```
**Conserver le jeton affiché** : c'est celui qui protège les écritures.

## 5. Service systemd
```bash
cp /opt/horizon/docs/deploy/horizon.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now horizon
systemctl status horizon --no-pager
```

## 6. TLS (Caddy)
```bash
cp /opt/horizon/docs/deploy/Caddyfile /etc/caddy/Caddyfile
# y remplacer mayela-crm.com par horizon.example.com, puis :
systemctl reload caddy
```

## 7. Vérifications
```bash
curl -sS https://horizon.example.com/api/v1/health
curl -sS -o /dev/null -w "%{http_code}\n" https://horizon.example.com/api/v1/projects   # 401 sans jeton
curl -sS -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer <TOKEN>" \
  https://horizon.example.com/api/v1/projects                                            # 200 avec jeton
```

## 8. Mise à jour ultérieure
```bash
cd /opt/horizon
sudo -u horizon git pull
sudo -u horizon .venv/bin/pip install -r backend/requirements.txt
npm ci && npm run build
systemctl restart horizon
```

## 9. Sécurité
- Aucun secret dans le dépôt ni dans l'interface : tout reste dans `backend/.env`.
- L'API refuse toute route `/api/...` (sauf `/health`) hors hôte local sans jeton.
- Après mise en ligne : scan de sécurité (lecture seule) avant les évolutions.
