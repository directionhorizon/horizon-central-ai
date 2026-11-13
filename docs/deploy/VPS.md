# Mise en ligne sur VPS — mayela-crm.com

Procédure minimale et reproductible. Ubuntu/Debian, accès root initial.

## 1. Utilisateur et dossiers

```bash
adduser --system --group --home /opt/horizon horizon
mkdir -p /var/lib/horizon
chown horizon:horizon /var/lib/horizon
```

## 2. Code

```bash
apt update && apt install -y python3 python3-venv git nodejs npm caddy
sudo -u horizon git clone <TON_DEPOT_PRIVE> /opt/horizon
cd /opt/horizon
sudo -u horizon python3 -m venv .venv
sudo -u horizon .venv/bin/pip install -r backend/requirements.txt
```

## 3. Interface compilée

```bash
cd /opt/horizon
npm ci
npm run build     # produit dist/, que le backend sert lui-même
```

## 4. Jeton (à générer UNE fois, ici sur le VPS)

```bash
cd /opt/horizon
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copier la valeur affichée dans `backend/.env` (fichier ignoré par Git) :

```bash
cat > /opt/horizon/backend/.env <<'EOF'
HORIZON_ADMIN_TOKEN=<la_valeur_generee>
HORIZON_CORS_ORIGINS=https://mayela-crm.com
HORIZON_DATABASE_PATH=/var/lib/horizon/horizon.db
EOF
chown horizon:horizon /opt/horizon/backend/.env
chmod 600 /opt/horizon/backend/.env
```

Ne jamais committer ce fichier, ni l'afficher dans un journal ou un rapport.

## 5. Service

```bash
cp /opt/horizon/docs/deploy/horizon.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now horizon
systemctl status horizon --no-pager
```

## 6. TLS

```bash
cp /opt/horizon/docs/deploy/Caddyfile /etc/caddy/Caddyfile
systemctl reload caddy
```

DNS : enregistrement `A` de `mayela-crm.com` vers l'IP du VPS. Ouvrir 80 et 443.

## 7. Vérifications

```bash
curl -sS https://mayela-crm.com/api/v1/health
curl -sS -o /dev/null -w "%{http_code}\n" https://mayela-crm.com/api/v1/projects
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer <jeton>" https://mayela-crm.com/api/v1/projects
```

Attendu : `200`, puis `401` sans jeton, puis `200` avec jeton.

## 8. Après la mise en ligne

Scanner avec Hackaiz (domaine prouvé, en lecture seule), corriger les constats
critiques, puis seulement envisager les évolutions fonctionnelles.
