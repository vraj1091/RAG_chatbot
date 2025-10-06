from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import asyncio
from sqlalchemy import text
from typing import List

from app.core.config import settings
from app.api.endpoints import auth, chat, documents
from app.db.database import engine, SessionLocal
from app.models import models

# Create database tables if they do not exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI RAG Chatbot API",
    description=(
        "A comprehensive RAG-powered chatbot with personalized knowledge base, "
        "Gemini API, and multi-format document support including images with OCR"
    ),
    version="2.0.0",
    debug=settings.debug,
)

# CORS middleware to allow cross-origin calls from configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload and vector store directories exist
os.makedirs(settings.upload_path, exist_ok=True)
os.makedirs(settings.vector_store_path, exist_ok=True)

# Mount static files to serve uploaded documents if directory exists
if os.path.exists(settings.upload_path):
    app.mount("/uploads", StaticFiles(directory=settings.upload_path), name="uploads")

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["🔐 Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["📄 Document Management"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["💬 RAG Chat & History"])

# Lazy Model Loader Class
class ModelLoader:
    def __init__(self):
        self.model = None
        self.loading = False
        self.loaded = False

    async def load_model(self):
        if self.loaded:
            return self.model
        if self.loading:
            while self.loading:
                await asyncio.sleep(0.1)
            return self.model
        self.loading = True
        try:
            print("🤖 Loading AI model...")
            # Replace the following sleep with your actual model loading logic
            await asyncio.sleep(2)

            # Example model loading (replace with your actual model code)
            # from sentence_transformers import SentenceTransformer
            # self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            self.model = "AI Model Loaded"  # Placeholder for actual model
            self.loaded = True
            print("✅ AI model loaded successfully!")
            return self.model
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise HTTPException(status_code=500, detail=f"Model loading failed: {str(e)}")
        finally:
            self.loading = False

model_loader = ModelLoader()

@app.get("/")
async def root():
    return {
        "message": "🤖 AI RAG Chatbot API with Gemini Integration",
        "version": "2.0.0",
        "features": [
            "🔐 User Authentication (Register/Login)",
            "📄 Multi-format Document Upload (PDF, DOCX, TXT, Images)",
            "🖼️ OCR for Image Text Extraction",
            "🧠 Real RAG Pipeline with ChromaDB Vector Database",
            "🤖 Gemini API Integration",
            "💬 Chat with History Management",
            "🔍 Context-aware Responses with Source Attribution",
        ],
        "docs": "/docs",
        "admin": "/admin",
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "✅ Connected"
    except Exception as e:
        db_status = f"❌ Error: {str(e)}"

    gemini_status = "✅ Configured" if settings.gemini_api_key else "⚠️ No API key"

    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path=settings.vector_store_path)
        vector_status = "✅ ChromaDB Connected"
    except Exception as e:
        vector_status = f"❌ ChromaDB Error: {str(e)}"

    return {
        "status": "healthy",
        "timestamp": "2025-09-22T10:13:00Z",
        "services": {
            "database": db_status,
            "gemini_api": gemini_status,
            "vector_db": vector_status,
            "upload_dir": f"✅ {settings.upload_path}",
            "vector_store": f"✅ {settings.vector_store_path}",
        },
    }

@app.get("/admin")
async def admin_info():
    """Admin information endpoint"""
    return {
        "app_name": "AI RAG Chatbot",
        "version": "2.0.0",
        "configuration": {
            "database_host": settings.dbhost,
            "database_name": settings.dbname,
            "vector_db": settings.vector_db_type,
            "embedding_model": settings.embedding_model,
            "max_file_size_mb": settings.max_file_size_mb,
            "allowed_file_types": settings.allowed_file_types_list,
            "gemini_configured": bool(settings.gemini_api_key),
        },
    }

# Model status endpoint
@app.get("/api/model/status")
async def get_model_status():
    return {
        "loaded": model_loader.loaded,
        "loading": model_loader.loading,
        "status": "loaded" if model_loader.loaded else "loading" if model_loader.loading else "not_loaded"
    }

# Preload model endpoint
@app.post("/api/model/preload")
async def preload_model(background_tasks: BackgroundTasks):
    if model_loader.loaded:
        return {"status": "already_loaded"}
    if model_loader.loading:
        return {"status": "loading"}
    background_tasks.add_task(model_loader.load_model)
    return {"status": "loading_started"}

# Include legacy item routes (optional)
from fastapi import APIRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    description: str

class ItemCreate(BaseModel):
    name: str
    description: str

items_db = [
    {"id": 1, "name": "Item 1", "description": "First item"},
    {"id": 2, "name": "Item 2", "description": "Second item"},
]

legacy_router = APIRouter()

@legacy_router.get("/api/items", response_model=List[Item])
async def get_items():
    return items_db

@legacy_router.post("/api/items", response_model=Item)
async def create_item(item: ItemCreate):
    new_id = max([item["id"] for item in items_db]) + 1 if items_db else 1
    new_item = {"id": new_id, **item.dict()}
    items_db.append(new_item)
    return new_item

@legacy_router.get("/api/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    item = next((item for item in items_db if item["id"] == item_id), None)
    if item is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Item not found")
    return item

app.include_router(legacy_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
