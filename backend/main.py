import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .database import create_tables
from .api import alerts, rca
from .models.schemas import APIResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Alert RCA Management System...")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Verify services
    from .services.llm_service import LLMService
    from .services.rag_service import RAGService
    
    llm_service = LLMService()
    rag_service = RAGService()
    
    if llm_service.is_available():
        logger.info("OLLAMA LLM service is available")
    else:
        logger.warning("OLLAMA LLM service is not available")
    
    if rag_service.is_available():
        logger.info("RAG service with ChromaDB is available")
    else:
        logger.warning("RAG service is not available")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Alert RCA Management System...")


# Create FastAPI application
app = FastAPI(
    title="Alert RCA Management System",
    description="Automated alert grouping and RCA generation system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(alerts.router, prefix="/api")
app.include_router(rca.router, prefix="/api")


@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint"""
    return APIResponse(
        success=True,
        message="Alert RCA Management System API",
        data={
            "version": "1.0.0",
            "docs": "/docs",
            "status": "running"
        }
    )


@app.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint"""
    try:
        from .services.llm_service import LLMService
        from .services.rag_service import RAGService
        from .database import engine
        
        # Check database connection
        db_status = "connected"
        try:
            engine.connect()
        except Exception:
            db_status = "disconnected"
        
        # Check LLM service
        llm_service = LLMService()
        llm_status = "available" if llm_service.is_available() else "unavailable"
        
        # Check RAG service
        rag_service = RAGService()
        rag_status = "available" if rag_service.is_available() else "unavailable"
        
        overall_status = "healthy" if all([
            db_status == "connected",
            llm_status == "available" or rag_status == "available"  # At least one service should work
        ]) else "degraded"
        
        return APIResponse(
            success=True,
            message=f"System status: {overall_status}",
            data={
                "status": overall_status,
                "database": db_status,
                "llm_service": llm_status,
                "rag_service": rag_status,
                "timestamp": "2025-01-01T00:00:00Z"  # You'd use actual timestamp
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return APIResponse(
            success=False,
            message="Health check failed",
            data={"error": str(e)}
        )


@app.get("/api/system/info", response_model=APIResponse)
async def get_system_info():
    """Get system information"""
    try:
        from .services.vector_service import VectorService
        
        vector_service = VectorService()
        vector_stats = vector_service.get_vector_db_stats()
        
        return APIResponse(
            success=True,
            message="System information retrieved",
            data={
                "application": "Alert RCA Management System",
                "version": "1.0.0",
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "llm": "OLLAMA/LLAMA3",
                "vector_db": "ChromaDB",
                "vector_stats": vector_stats,
                "settings": {
                    "alert_grouping_window": settings.alert_grouping_window_minutes,
                    "similarity_threshold": settings.similarity_threshold,
                    "ollama_model": settings.ollama_model
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return APIResponse(
        success=False,
        message="Endpoint not found",
        data={"path": str(request.url.path)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return APIResponse(
        success=False,
        message="Internal server error",
        data={"error": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    )
