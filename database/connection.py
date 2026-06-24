import os
from typing import Generator

import psycopg2
import psycopg2.extensions


def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Generador para FastAPI Depends.
    Conecta al PostgreSQL local del contenedor (trust auth, sin password).
    """
    host     = os.getenv("DB_HOST",     "localhost")
    port     = os.getenv("DB_PORT",     "5432")
    dbname   = os.getenv("DB_NAME",     "blogdb")
    user     = os.getenv("DB_USER",     "postgres")
    password = os.getenv("DB_PASSWORD", "")

    try:
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            dbname=dbname,
            user=user,
            password=password,
        )
    except psycopg2.OperationalError as exc:
        raise RuntimeError(
            f"No se pudo conectar a PostgreSQL en {host}:{port}/{dbname} — {exc}"
        ) from exc

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
