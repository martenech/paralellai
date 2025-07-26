from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import torch

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings
    
    def chunk_text(self, text: str, max_length: int = 512) -> List[str]:
        """Split text into chunks for embedding"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1
            if current_length + word_length > max_length:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks if chunks else [text]