import os
from typing import Generator

import psycopg2
import psycopg2.extensions


def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Generador para FastAPI Depends.
    Lee las variables de entorno en cada llamada (no al importar el módulo)
    para garantizar que Render las haya inyectado antes de conectar.
    Prioriza DATABASE_URL (Render managed PostgreSQL); usa vars individuales
    como fallback para desarrollo local.
    """
    database_url = os.getenv("DATABASE_URL")

    try:
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            host     = os.getenv("DB_HOST",     "localhost")
            port     = os.getenv("DB_PORT",     "5432")
            dbname   = os.getenv("DB_NAME",     "blogdb")
            user     = os.getenv("DB_USER",     "postgres")
            password = os.getenv("DB_PASSWORD", "postgres")

            conn = psycopg2.connect(
                host=host,
                port=int(port),
                dbname=dbname,
                user=user,
                password=password,
            )
    except psycopg2.OperationalError as exc:
        db_target = database_url or f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        raise RuntimeError(
            f"No se pudo conectar a PostgreSQL en '{db_target}'. "
            "Verificá que DATABASE_URL esté configurada en Render → Web Service → Environment."
        ) from exc

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
