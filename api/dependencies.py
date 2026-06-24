import psycopg2
from psycopg2.extensions import connection
from fastapi import Depends
from database.connection import get_db_connection
from repositories.article_repository import ArticleRepository
from services.article_service import ArticleService

def get_article_repository(conn: connection = Depends(get_db_connection)) -> ArticleRepository:
    return ArticleRepository(conn=conn)

def get_article_service(repo: ArticleRepository = Depends(get_article_repository)) -> ArticleService:
    return ArticleService(repository=repo)
