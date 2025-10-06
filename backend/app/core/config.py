from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database Configuration (Separate fields)
    dbhost: str = "34.170.243.16"
    dbport: int = 3306
    dbname: str = "rag_chatbot"
    dbuser: str = "root"
    dbpassword: str = "vraj10@PA"

    # Security
    secret_key: str = "your-super-secure-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    frontend_url: str = "http://localhost:3000", "http://172.28.0.1:3000/"

    # AI Configuration - Gemini API
    gemini_api_key: str = "AIzaSyCsr9fjAeHEJGvfOFhsBcpeu-wOkQjHGmE"
    gemini_model_name: str = "projects/generativelanguage-ga/locations/us-central1/publishers/google/models/gemini-2.5-flash"

    # Vector Database
    vector_db_type: str = "chromadb"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # File Upload
    max_file_size_mb: int = 25
    allowed_file_types: str = "pdf,txt,docx,png,jpg,jpeg"
    upload_dir: str = "uploads"
    vector_store_dir: str = "vector_stores"

    # OCR Configuration
    tesseract_path: str = "/usr/bin/tesseract"
    poppler_path: str = "/usr/bin"

    # Application
    debug: bool = False
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """
        Build the full DATABASE_URL for SQLAlchemy.
        """
        user = self.dbuser
        pwd = self.dbpassword.replace("@", "%40")
        host = self.dbhost
        port = self.dbport
        db = self.dbname
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"

    @property
    def allowed_file_types_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.allowed_file_types.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cors_origins(self) -> List[str]:
        # include both localhost and 127.0.0.1
        return [self.frontend_url, "http://127.0.0.1:3000", "http://localhost:3000","https://rag-chatbot-frontend-oak8.onrender.com"]

    @property
    def upload_path(self) -> str:
        os.makedirs(self.upload_dir, exist_ok=True)
        return os.path.abspath(self.upload_dir)

    @property
    def vector_store_path(self) -> str:
        os.makedirs(self.vector_store_dir, exist_ok=True)
        return os.path.abspath(self.vector_store_dir)

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignore any unexpected env vars


settings = Settings()
