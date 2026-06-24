#!/bin/bash
set -e

# Detectar versión de PostgreSQL instalada (ej: "15")
PG_VERSION=$(ls /usr/lib/postgresql/)
INITDB="/usr/lib/postgresql/${PG_VERSION}/bin/initdb"
PG_CTL="/usr/lib/postgresql/${PG_VERSION}/bin/pg_ctl"
PG_DATA="/var/lib/postgresql/data"
DB_NAME="blogdb"

echo ">>> PostgreSQL ${PG_VERSION} detectado"

# Preparar directorio de datos
mkdir -p "$PG_DATA"
chown postgres:postgres "$PG_DATA"

# Preparar log
touch /var/log/postgresql.log
chown postgres:postgres /var/log/postgresql.log

# Inicializar cluster solo si es la primera vez
if [ ! -f "${PG_DATA}/PG_VERSION" ]; then
    echo ">>> Inicializando cluster PostgreSQL..."
    su postgres -c "$INITDB -D $PG_DATA --auth=trust --no-instructions"
fi

# Arrancar PostgreSQL en background (como usuario postgres)
echo ">>> Iniciando PostgreSQL..."
su postgres -c "$PG_CTL start -D $PG_DATA -l /var/log/postgresql.log -w -t 30"

# Crear base de datos si no existe
echo ">>> Configurando base de datos '${DB_NAME}'..."
su postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\" | grep -q 1" \
    || su postgres -c "createdb ${DB_NAME}"

# Variables de conexión para la API (localhost, trust auth, sin password)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=$DB_NAME
export DB_USER=postgres
export DB_PASSWORD=

echo ">>> Iniciando API en puerto ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
