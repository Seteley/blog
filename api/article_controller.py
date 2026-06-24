from fastapi import APIRouter, Depends, HTTPException
from typing import List
from models.article import ArticleCreate, ArticleResponse
from services.article_service import ArticleService
from api.dependencies import get_article_service

router = APIRouter(prefix="/articles", tags=["Articles"])

@router.post("/", response_model=ArticleResponse, status_code=201)
def create_article(
    article: ArticleCreate,
    service: ArticleService = Depends(get_article_service)
):
    try:
        return service.create_article(article)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/", response_model=List[ArticleResponse])
def get_articles(
    service: ArticleService = Depends(get_article_service)
):
    try:
        return service.get_articles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
