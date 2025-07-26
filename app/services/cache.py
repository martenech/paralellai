import redis
import json
from typing import Optional, Dict, Any, List
import os

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        self.default_ttl = 3600  # 1 hour
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from cache"""
        data = self.redis_client.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    def set_session(self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None):
        """Set session data in cache"""
        self.redis_client.setex(
            f"session:{session_id}",
            ttl or self.default_ttl,
            json.dumps(data)
        )
    
    def get_context(self, conversation_id: str) -> Optional[List[int]]:
        """Get LLM context for conversation"""
        data = self.redis_client.get(f"context:{conversation_id}")
        return json.loads(data) if data else None
    
    def set_context(self, conversation_id: str, context: List[int], ttl: Optional[int] = None):
        """Set LLM context for conversation"""
        self.redis_client.setex(
            f"context:{conversation_id}",
            ttl or self.default_ttl,
            json.dumps(context)
        )
    
    def delete_session(self, session_id: str):
        """Delete session from cache"""
        self.redis_client.delete(f"session:{session_id}")
    
    def delete_context(self, conversation_id: str):
        """Delete context from cache"""
        self.redis_client.delete(f"context:{conversation_id}")