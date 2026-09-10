from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes.query import router as query_router
from app.core.config import settings
from app.services.retrieval import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events handle startup and shutdown logic.
    We initialize the ChromaDB connection here so it happens exactly once.
    """
    print(f"Starting up {settings.PROJECT_NAME}...")
    init_db()
    
    yield # The application runs while yielded here
    
    print("Shutting down API...")

# Initialize the FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Attach CORS middleware to allow the frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register our API endpoints
app.include_router(query_router)