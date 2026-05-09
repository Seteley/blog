from fastapi import FastAPI
from api.article_controller import router as article_router
from database.connection import get_db_connection
from repositories.article_repository import ArticleRepository
from services.article_service import ArticleService

app = FastAPI(title="Blog API - N-Tier Architecture", version="1.0.0")

@app.on_event("startup")
def startup_event():
    """
    Se ejecuta al inicio para asegurar que la tabla existe en la BD.
    En producción, usaríamos herramientas como Alembic, pero aquí 
    lo hacemos manualmente como prueba de la arquitectura.
    """
    try:
        # Obtenemos manualmente una conexión para inicializar
        generator = get_db_connection()
        conn = next(generator)
        repo = ArticleRepository(conn)
        service = ArticleService(repo)
        service.ensure_db_initialized()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Registrar routers (Controllers)
app.include_router(article_router)

@app.get("/")
def root():
    return {"message": "Welcome to Blog API (N-Tier)"}
