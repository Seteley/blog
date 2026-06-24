from datetime import datetime

from pydantic import BaseModel, Field


class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, examples=["Mi primer artículo"])
    content: str = Field(..., min_length=10, examples=["Contenido detallado del artículo..."])


class ArticleResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
