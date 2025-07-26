import httpx
import numpy as np
from typing import List, Optional
import json

class OllamaEmbeddingService:
    def __init__(self, 
                 base_url: str = None,
                 model: str = "nomic-embed-text"):
        """
        Embedding service using Ollama's embedding models
        
        Args:
            base_url: Ollama API base URL
            model: Embedding model name (nomic-embed-text)
        """
        if base_url is None:
            import os
            base_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        
        self.base_url = base_url
        self.model = model
        self.client = httpx.Client(timeout=30.0)
        self.dimension = 768  # nomic-embed-text dimension
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text using Ollama"""
        response = self.client.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            }
        )
        response.raise_for_status()
        
        embedding = response.json()["embedding"]
        return np.array(embedding)
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
    def get_sentence_embedding_dimension(self) -> int:
        """Return embedding dimension"""
        return self.dimension
    
    def chunk_text(self, text: str, max_length: int = 8192) -> List[str]:
        """
        Split text into chunks for embedding
        nomic-embed-text supports up to 8192 tokens
        """
        # Simple character-based chunking
        # In production, use proper tokenization
        chunks = []
        
        if len(text) <= max_length:
            return [text]
        
        # Split by sentences first
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def __del__(self):
        self.client.close()