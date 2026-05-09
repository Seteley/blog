from typing import List
from models.article import ArticleCreate, ArticleResponse
from repositories.article_repository import ArticleRepository

class ArticleService:
    def __init__(self, repository: ArticleRepository):
        self._repository = repository

    def create_article(self, article: ArticleCreate) -> ArticleResponse:
        """
        Lógica de negocio para crear un artículo.
        Aquí se incluirían validaciones complejas si las hubiera.
        """
        # Por ejemplo, una validación simple de negocio (simulada)
        if not article.title.strip():
            raise ValueError("El título del artículo no puede estar vacío.")
            
        return self._repository.create(article)

    def get_articles(self) -> List[ArticleResponse]:
        """
        Lógica de negocio para obtener todos los artículos.
        """
        return self._repository.get_all()
        
    def ensure_db_initialized(self):
        """
        Delega la inicialización de la tabla.
        """
        self._repository.init_db()
