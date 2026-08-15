#!/bin/sh
set -eu

for banco in pedidos estoque pagamentos; do
  psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE $banco OWNER $POSTGRES_USER;"
done
