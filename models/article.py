from pydantic import BaseModel, Field

class ArticleCreate(BaseModel):
    title: str = Field(..., title="Title of the article", max_length=200)
    content: str = Field(..., title="Content of the article")

class ArticleResponse(BaseModel):
    id: int
    title: str
    content: str

    class Config:
        from_attributes = True
