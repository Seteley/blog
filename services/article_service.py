from typing import List

from models.article import ArticleCreate, ArticleResponse
from repositories.article_repository import ArticleRepository


class ArticleService:
    """
    BLL — valida reglas de negocio antes de delegar al repositorio.
    No conoce psycopg2 ni detalles de persistencia.
    """

    def __init__(self, repository: ArticleRepository) -> None:
        self._repository = repository

    def get_articles(self) -> List[ArticleResponse]:
        return self._repository.get_all()

    def create_article(self, article: ArticleCreate) -> ArticleResponse:
        self._validate(article)
        return self._repository.create(article)

    def ensure_db_initialized(self) -> None:
        self._repository.init_db()

    @staticmethod
    def _validate(article: ArticleCreate) -> None:
        if not article.title.strip():
            raise ValueError("El título no puede estar vacío.")
        if len(article.title.strip()) < 3:
            raise ValueError("El título debe tener al menos 3 caracteres.")
        if len(article.content.strip()) < 10:
            raise ValueError("El contenido debe tener al menos 10 caracteres.")
