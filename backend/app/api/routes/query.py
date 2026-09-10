from fastapi import APIRouter
from app.schemas.query import QueryRequest, QueryResponse
from app.services.retrieval import retrieve_context
from app.services.generation import generate_rag_answer
import re


router = APIRouter()


@router.get("/health")
def health_check():
    """Simple endpoint to verify the API is running."""
    return {
        "status": "healthy",
        "message": "Hardware RAG API is up and running!"
    }


@router.post("/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    """Connects the user question to the RAG pipeline."""

    # 1. Retrieve relevant context
    context = retrieve_context(request.question)

    # 2. Generate grounded answer
    answer = generate_rag_answer(
        request.question,
        context
    )

    # 3. Extract unique source filenames
    raw_sources = re.findall(
        r"Source: \[([^|]+)\|",
        context
    )

    unique_sources = list(
        dict.fromkeys(
            s.strip() for s in raw_sources
        )
    )

    # 4. Return answer + sources
    return QueryResponse(
        answer=answer,
        sources=unique_sources
    )