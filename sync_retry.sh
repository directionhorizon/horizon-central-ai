#!/bin/bash
T=$(grep '^HORIZON_ADMIN_TOKEN=' /opt/horizon/backend/.env | cut -d= -f2- | tr -d '\r')
echo "len=${#T}"
curl -s -o /dev/null -w "diag=%{http_code}\n" -H "X-Horizon-Token: $T" https://horizon.mayela-crm.com/api/v1/admin/diagnostics
curl -s -X POST -H "X-Horizon-Token: $T" https://horizon.mayela-crm.com/api/v1/sync/retry
echo
