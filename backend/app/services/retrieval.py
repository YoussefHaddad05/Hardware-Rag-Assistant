import chromadb
from chromadb.utils import embedding_functions
from app.core.config import settings

# Global variables to hold our database connection
chroma_client = None
collection = None

def init_db():
    """Initializes the ChromaDB connection once during app startup."""
    global chroma_client, collection
    
    chroma_client = chromadb.PersistentClient(path=settings.VECTOR_STORE_PATH)
    
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.EMBEDDING_MODEL
    )
    
    collection = chroma_client.get_collection(
        name=settings.COLLECTION_NAME,
        embedding_function=embedding_func
    )
    print(f"Success: Connected to ChromaDB collection '{settings.COLLECTION_NAME}'")

def retrieve_context(query: str) -> str:
    """Retrieves chunks from the vector database and formats them with citations."""
    
    # Defensive check to ensure the DB is loaded before querying
    if collection is None:
        raise RuntimeError("ChromaDB has not been initialized. Call init_db() first.")

    results = collection.query(
        query_texts=[query],
        n_results=settings.RETRIEVAL_TOP_K
    )
    
    formatted_context = ""
    for i in range(len(results['documents'][0])):
        text = results['documents'][0][i]
        metadata = results['metadatas'][0][i]
        
        formatted_context += (
            f"Source: [{metadata['source']} | "
            f"Page: {metadata['page']} | "
            f"Chunk: {metadata['chunk_id']}]\n"
            f"Text: {text}\n\n"
        )
        
    return formatted_context