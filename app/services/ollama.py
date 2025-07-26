import httpx
from typing import Dict, List, Optional
import json

class OllamaService:
    def __init__(self, base_url: str = None):
        if base_url is None:
            import os
            base_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        self.base_url = base_url
        self.client = httpx.Client(timeout=60.0)
    
    def generate(self, 
                 model: str,
                 prompt: str,
                 system: Optional[str] = None,
                 context: Optional[List[int]] = None,
                 temperature: float = 0.7) -> Dict:
        """Generate response from Ollama"""
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }
        
        if system:
            payload["system"] = system
        
        if context:
            payload["context"] = context
        
        response = self.client.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def chat(self,
             model: str,
             messages: List[Dict[str, str]],
             temperature: float = 0.7) -> Dict:
        """Chat with Ollama using conversation history"""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        response = self.client.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def list_models(self) -> List[Dict]:
        """List available models"""
        response = self.client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        return response.json()["models"]
    
    def __del__(self):
        self.client.close()