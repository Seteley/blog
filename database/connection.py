import os
import psycopg2
from typing import Generator

def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Generador de conexión a PostgreSQL utilizando psycopg2.
    Se utiliza como dependencia en FastAPI para asegurar que cada petición tenga su conexión
    y se cierre correctamente al finalizar.
    """
    host = os.getenv("DB_SERVER", "localhost")
    database = os.getenv("DB_NAME", "blog_db")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "Your_Strong_Password_123!")
    port = os.getenv("DB_PORT", "5432")
    
    conn = None
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        yield conn
    finally:
        if conn:
            conn.close()
