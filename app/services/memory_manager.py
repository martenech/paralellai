from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
from datetime import datetime, timedelta, timezone

from app.db import Message, MessageEmbedding
from app.services import EmbeddingService, OllamaService

class MemoryManager:
    def __init__(self, 
                 embedding_service: EmbeddingService,
                 similarity_threshold: float = 0.7,
                 max_memories: int = 10,
                 time_decay_days: int = 30):
        """
        Long-term memory manager for LLM
        
        Args:
            embedding_service: Service for generating embeddings
            similarity_threshold: Minimum similarity score to consider a match
            max_memories: Maximum number of memories to retrieve
            time_decay_days: Days after which memory relevance decays
        """
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.max_memories = max_memories
        self.time_decay_days = time_decay_days
    
    def find_similar_questions(self, 
                             query: str, 
                             db: Session,
                             user_id: Optional[str] = None,
                             exclude_conversation_id: Optional[str] = None) -> List[Dict]:
        """
        Find similar questions from history using semantic search
        
        Returns list of similar Q&A pairs with metadata
        """
        # Generate embedding for query
        query_embedding = self.embedding_service.embed_text(query)
        
        # Build SQL query for vector similarity search
        sql = text("""
            WITH similar_messages AS (
                SELECT 
                    me.message_id,
                    me.chunk_text,
                    1 - (me.embedding <=> CAST(:query_embedding AS vector)) as similarity,
                    m.content as full_content,
                    m.role,
                    m.created_at,
                    m.conversation_id,
                    c.user_id
                FROM message_embeddings me
                JOIN messages m ON me.message_id = m.id
                JOIN conversations c ON m.conversation_id = c.id
                WHERE 
                    m.role = 'user'
                    AND 1 - (me.embedding <=> CAST(:query_embedding AS vector)) > :threshold
                    AND (:user_id IS NULL OR c.user_id = :user_id)
                    AND (:exclude_conv_id IS NULL OR m.conversation_id != :exclude_conv_id)
                ORDER BY similarity DESC
                LIMIT :limit
            )
            SELECT 
                sm.*,
                response.content as response_content,
                response.created_at as response_created_at
            FROM similar_messages sm
            LEFT JOIN LATERAL (
                SELECT content, created_at
                FROM messages
                WHERE 
                    conversation_id = sm.conversation_id
                    AND role = 'assistant'
                    AND created_at > sm.created_at
                ORDER BY created_at ASC
                LIMIT 1
            ) response ON true
            WHERE response.content IS NOT NULL
        """)
        
        results = db.execute(sql, {
            'query_embedding': query_embedding.tolist(),
            'threshold': self.similarity_threshold,
            'user_id': user_id,
            'exclude_conv_id': exclude_conversation_id,
            'limit': self.max_memories
        }).fetchall()
        
        memories = []
        for row in results:
            # Calculate time decay factor
            now = datetime.now(timezone.utc)
            days_old = (now - row.created_at).days
            time_factor = max(0, 1 - (days_old / self.time_decay_days))
            
            # Adjust similarity with time decay
            adjusted_similarity = row.similarity * (0.7 + 0.3 * time_factor)
            
            memories.append({
                'question': row.full_content,
                'answer': row.response_content,
                'similarity': row.similarity,
                'adjusted_similarity': adjusted_similarity,
                'created_at': row.created_at,
                'conversation_id': row.conversation_id,
                'user_id': row.user_id
            })
        
        # Sort by adjusted similarity
        memories.sort(key=lambda x: x['adjusted_similarity'], reverse=True)
        
        return memories
    
    def check_duplicate_question(self, 
                               query: str, 
                               db: Session,
                               user_id: Optional[str] = None,
                               duplicate_threshold: float = 0.9) -> Optional[Dict]:
        """
        Check if this exact question was already asked
        
        Returns the previous answer if found, None otherwise
        """
        memories = self.find_similar_questions(
            query, 
            db, 
            user_id=user_id,
            exclude_conversation_id=None
        )
        
        # Check for very high similarity (likely duplicate)
        if memories and memories[0]['similarity'] >= duplicate_threshold:
            return memories[0]
        
        return None
    
    def get_relevant_context(self,
                           query: str,
                           db: Session,
                           conversation_id: str,
                           user_id: Optional[str] = None) -> Dict:
        """
        Get relevant context from long-term memory
        
        Returns:
            - is_duplicate: Whether this is a duplicate question
            - previous_answer: Previous answer if duplicate
            - relevant_memories: List of relevant Q&A pairs
            - suggested_context: Context to include in prompt
        """
        # Check for duplicate first
        duplicate = self.check_duplicate_question(query, db, user_id)
        
        if duplicate and duplicate['conversation_id'] != conversation_id:
            return {
                'is_duplicate': True,
                'previous_answer': duplicate['answer'],
                'duplicate_info': {
                    'similarity': duplicate['similarity'],
                    'asked_at': duplicate['created_at'],
                    'conversation_id': duplicate['conversation_id']
                },
                'relevant_memories': [],
                'suggested_context': None
            }
        
        # Get relevant memories (excluding current conversation)
        memories = self.find_similar_questions(
            query, 
            db, 
            user_id=user_id,
            exclude_conversation_id=conversation_id
        )
        
        # Filter out near-duplicates from memories
        filtered_memories = []
        for memory in memories:
            if memory['similarity'] < duplicate_threshold:
                filtered_memories.append(memory)
        
        # Build context from memories
        context_parts = []
        if filtered_memories:
            context_parts.append("Relevant information from previous conversations:")
            for i, memory in enumerate(filtered_memories[:3]):  # Top 3 memories
                context_parts.append(f"\nQ: {memory['question']}")
                context_parts.append(f"A: {memory['answer'][:200]}...")
        
        suggested_context = "\n".join(context_parts) if context_parts else None
        
        return {
            'is_duplicate': False,
            'previous_answer': None,
            'duplicate_info': None,
            'relevant_memories': filtered_memories,
            'suggested_context': suggested_context
        }
    
    def format_response_with_memory(self,
                                  query: str,
                                  memory_context: Dict,
                                  ollama_service: OllamaService,
                                  model: str = "llama3.2") -> str:
        """
        Format response considering memory context
        """
        if memory_context['is_duplicate']:
            # Return previous answer with acknowledgment
            dup_info = memory_context['duplicate_info']
            days_ago = (datetime.now(timezone.utc) - dup_info['asked_at']).days
            
            time_ref = "earlier today" if days_ago == 0 else f"{days_ago} days ago"
            
            return (f"I've already answered this question {time_ref}. "
                   f"Here's my previous response:\n\n"
                   f"{memory_context['previous_answer']}")
        
        # Build enhanced prompt with context
        enhanced_prompt = ""
        if memory_context['suggested_context']:
            enhanced_prompt = f"{memory_context['suggested_context']}\n\n"
        enhanced_prompt += f"Current question: {query}"
        
        # Generate new response
        response = ollama_service.generate(
            model=model,
            prompt=enhanced_prompt,
            temperature=0.7
        )
        
        return response['response']