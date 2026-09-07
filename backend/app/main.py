from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import health, auth, files, search, rag
import app.models  # Ensures models are imported so Base knows about them

# Safely attempt to create database tables on startup
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Notice: Database table initialization skipped or deferred: {e}")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Backend API for secure file retrieval, semantic search, and RAG.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
origins = [settings.FRONTEND_ORIGIN]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(search.router)
app.include_router(rag.router)


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/api/v1/health"
    }