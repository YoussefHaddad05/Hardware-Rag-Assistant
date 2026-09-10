import json 
from pydantic_settings import BaseSettings, SettingsConfigDict 
from pathlib import Path 
 
class Settings(BaseSettings): 
    # Standard API settings 
    PROJECT_NAME: str = "Hardware RAG Assistant API" 
    API_VERSION: str = "1.0.0" 
     
    # CORS settings 
    BACKEND_CORS_ORIGINS: list[str] = [] 
     
    # RAG Configuration 
    RAG_CONFIG_PATH: str = "data/vector_store/rag_config.json" 
     
    # These will be populated dynamically by reading the JSON file 
    VECTOR_STORE_PATH: str = "" 
    COLLECTION_NAME: str = "" 
    EMBEDDING_MODEL: str = "" 
    LLM_MODEL: str = "" 
    RETRIEVAL_TOP_K: int = 8 
 
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    ) 
 
    def load_rag_config(self):
        """Loads the exported JSON configuration from Phase 2."""
        config_file = Path(self.RAG_CONFIG_PATH)

        if config_file.exists():
            with open(config_file, "r") as f:
                rag_data = json.load(f)
                 
            self.VECTOR_STORE_PATH = rag_data.get("vector_store_path", "")
            self.COLLECTION_NAME = rag_data.get("collection_name", "")
            self.EMBEDDING_MODEL = rag_data.get("embedding_model", "")
            self.LLM_MODEL = rag_data.get("llm_model", "")
            self.RETRIEVAL_TOP_K = rag_data.get("retrieval_top_k", 8)

            print("Successfully loaded RAG configuration!")
        else:
            print(f"Warning: RAG config file not found at {self.RAG_CONFIG_PATH}")
 
settings = Settings()
settings.load_rag_config()