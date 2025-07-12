import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "alert_rca_db"
    db_user: str = "postgres"
    db_password: str = "password"
    database_url: str = "postgresql://postgres:password@localhost:5432/alert_rca_db"
    
    # OLLAMA
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    # ChromaDB
    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    chromadb_persist_dir: str = "./chromadb_data"
    
    # FastAPI
    backend_host: str = "localhost"
    backend_port: int = 8000
    debug: bool = True
    
    # Security
    secret_key: str = "your-secret-key-change-this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Alert Processing
    alert_grouping_window_minutes: int = 5
    similarity_threshold: float = 0.8
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
