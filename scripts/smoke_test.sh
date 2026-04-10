#!/usr/bin/env bash

set -e

BASE_URL="http://localhost:8000"
EMAIL="superadmin@lab.com"
PASSWORD="changeme"

echo "== Verificando health =="
curl -f "$BASE_URL/health"
echo
echo "OK: /health responde"

echo "== Haciendo login =="

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")

echo "Respuesta login:"
echo "$LOGIN_RESPONSE"
echo

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("access_token", ""))')

if [ -z "$TOKEN" ]; then
  echo "ERROR: no se obtuvo access_token en el login"
  exit 1
fi

echo "OK: login exitoso"

echo "== Verificando /auth/me =="
curl -f -H "Authorization: Bearer $TOKEN" "$BASE_URL/auth/me"
echo
echo "OK: /auth/me responde"

echo "== Verificando /groups =="
curl -f -H "Authorization: Bearer $TOKEN" "$BASE_URL/groups"
echo
echo "OK: /groups responde"

echo "== Verificando /members =="
curl -f -H "Authorization: Bearer $TOKEN" "$BASE_URL/members"
echo
echo "OK: /members responde"

echo
echo "SMOKE TEST OK"