import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

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

logger = logging.getLogger("app.main")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Backend API for secure file retrieval, semantic search, and RAG.",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
def startup_checks():
    from app.services.text_extraction_service import verify_tesseract_installation
    tess_path, tess_ver = verify_tesseract_installation()
    if tess_path:
        logger.info("Tesseract OCR verified: %s (%s)", tess_path, tess_ver)
    else:
        logger.warning(
            "Tesseract binary not found. OCR cannot be performed on images or scanned PDFs. "
            "Ensure tesseract-ocr is installed or TESSERACT_CMD is set."
        )

# Configure CORS
origins = [origin.strip() for origin in settings.FRONTEND_ORIGIN.split(",") if origin.strip()]

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