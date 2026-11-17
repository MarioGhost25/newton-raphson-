#!/bin/sh
set -eu

# Reejecutable sobre un volumen existente: nunca elimina bases ni modifica claves.
: "${POSTGRES_TEST_DB:?Falta POSTGRES_TEST_DB}"
case "$POSTGRES_TEST_DB" in
  ''|*[!a-zA-Z0-9_]*) echo "POSTGRES_TEST_DB debe usar letras, números o guion bajo." >&2; exit 1 ;;
esac
if [ "$POSTGRES_TEST_DB" = "$POSTGRES_DB" ]; then
  echo "La base de pruebas debe ser distinta de POSTGRES_DB." >&2
  exit 1
fi

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 --set=test_db="$POSTGRES_TEST_DB" --set=db_owner="$POSTGRES_USER" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'test_db', :'db_owner')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'test_db')
\gexec
SQL
