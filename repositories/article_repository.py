from datetime import datetime
from typing import List

import psycopg2.extensions

from models.article import ArticleCreate, ArticleResponse


class ArticleRepository:
    """
    DAL — acceso a PostgreSQL con SQL puro y mapeo manual de filas.
    Recibe la conexión por inyección desde la capa de DI.
    """

    def __init__(self, conn: psycopg2.extensions.connection) -> None:
        self._conn = conn

    def get_all(self) -> List[ArticleResponse]:
        with self._conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, content, created_at FROM articles ORDER BY created_at DESC"
            )
            return [self._map_row(row) for row in cursor.fetchall()]

    def create(self, article: ArticleCreate) -> ArticleResponse:
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO articles (title, content)
                VALUES (%s, %s)
                RETURNING id, title, content, created_at
                """,
                (article.title.strip(), article.content.strip()),
            )
            return self._map_row(cursor.fetchone())

    def init_db(self) -> None:
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id         SERIAL       PRIMARY KEY,
                    title      VARCHAR(200) NOT NULL,
                    content    TEXT         NOT NULL,
                    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                )
                """
            )

    @staticmethod
    def _map_row(row: tuple) -> ArticleResponse:
        return ArticleResponse(
            id=int(row[0]),
            title=str(row[1]),
            content=str(row[2]),
            created_at=row[3] if isinstance(row[3], datetime) else datetime.fromisoformat(str(row[3])),
        )
