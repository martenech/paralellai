import os
from typing import Optional

class Config:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://llm_user:llm_password@postgres:5432/llm_memory"
    )
    
    # Ollama
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    OLLAMA_CHAT_MODEL: str = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
    
    # Embeddings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "ollama")  # "sentence_transformers" or "ollama"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))  # 384 for all-MiniLM-L6-v2, 768 for nomic-embed-text
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    
    # Reflection Worker
    REFLECTION_ENABLED: bool = os.getenv("REFLECTION_ENABLED", "true").lower() == "true"
    REFLECTION_INTERVAL: int = int(os.getenv("REFLECTION_INTERVAL", "300"))  # seconds
    REFLECTION_BATCH_SIZE: int = int(os.getenv("REFLECTION_BATCH_SIZE", "10"))
    
    # Memory Manager
    MEMORY_SIMILARITY_THRESHOLD: float = float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.7"))
    MEMORY_DUPLICATE_THRESHOLD: float = float(os.getenv("MEMORY_DUPLICATE_THRESHOLD", "0.9"))
    MEMORY_MAX_RESULTS: int = int(os.getenv("MEMORY_MAX_RESULTS", "10"))
    MEMORY_TIME_DECAY_DAYS: int = int(os.getenv("MEMORY_TIME_DECAY_DAYS", "30"))

config = Config()