from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.article_controller import router as article_router
from database.connection import get_db_connection
from repositories.article_repository import ArticleRepository
from services.article_service import ArticleService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea la tabla articles si no existe al arrancar
    try:
        gen = get_db_connection()
        conn = next(gen)
        try:
            ArticleService(ArticleRepository(conn)).ensure_db_initialized()
            conn.commit()
            print("Database schema initialized.")
        finally:
            conn.close()
    except Exception as exc:
        print(f"Warning: could not initialize DB schema — {exc}")
    yield


app = FastAPI(
    title="Blog API",
    description="Backend N-Tier con FastAPI y PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(article_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "ok"}
