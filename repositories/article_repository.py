import psycopg2
from psycopg2.extensions import connection
from typing import List
from models.article import ArticleCreate, ArticleResponse

class ArticleRepository:
    def __init__(self, conn: connection):
        self._conn = conn

    def create(self, article: ArticleCreate) -> ArticleResponse:
        """
        Ejecuta la creación del artículo utilizando SQL puro en PostgreSQL.
        """
        cursor = self._conn.cursor()
        
        query = """
            INSERT INTO Articles (Title, Content)
            VALUES (%s, %s)
            RETURNING Id
        """
        
        cursor.execute(query, (article.title, article.content))
        row = cursor.fetchone()
        new_id = row[0] if row else 0
        
        self._conn.commit()
        cursor.close()
        
        return ArticleResponse(
            id=new_id,
            title=article.title,
            content=article.content
        )

    def get_all(self) -> List[ArticleResponse]:
        """
        Obtiene todos los artículos de la base de datos usando SQL puro y mapeo manual.
        """
        cursor = self._conn.cursor()
        query = "SELECT Id, Title, Content FROM Articles"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        articles = []
        for row in rows:
            # Mapeo manual de la fila al objeto Pydantic
            article = ArticleResponse(
                id=row[0],
                title=row[1],
                content=row[2]
            )
            articles.append(article)
            
        cursor.close()
        return articles
        
    def init_db(self):
        """
        Método de utilidad para crear la tabla si no existe.
        """
        cursor = self._conn.cursor()
        query = """
        CREATE TABLE IF NOT EXISTS Articles (
            Id SERIAL PRIMARY KEY,
            Title VARCHAR(200) NOT NULL,
            Content TEXT NOT NULL
        )
        """
        cursor.execute(query)
        self._conn.commit()
        cursor.close()
