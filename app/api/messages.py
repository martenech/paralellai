from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db, Conversation, Message, MessageEmbedding
from app.services import OllamaService, OllamaEmbeddingService, CacheService, MemoryManager
from app.config import config

router = APIRouter()
ollama_service = OllamaService()

# Initialize embedding service based on config
if config.EMBEDDING_PROVIDER == "ollama":
    embedding_service = OllamaEmbeddingService(
        model=config.EMBEDDING_MODEL
    )
else:
    from app.services import EmbeddingService
    embedding_service = EmbeddingService()

cache_service = CacheService()
memory_manager = MemoryManager(embedding_service)

class MessageCreate(BaseModel):
    conversation_id: str
    content: str
    model: str = "llama3.2"
    temperature: float = 0.7

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    token_count: int

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    context_used: bool = False
    memory_used: bool = False
    is_duplicate: bool = False

@router.post("/chat", response_model=ChatResponse)
def chat(
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    """Send a message and get AI response"""
    # Verify conversation exists
    conversation = db.query(Conversation).filter(
        Conversation.id == message.conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Save user message
    user_msg = Message(
        conversation_id=message.conversation_id,
        role="user",
        content=message.content,
        token_count=len(message.content.split())
    )
    db.add(user_msg)
    db.flush()  # Flush to get the ID
    
    # Generate and save embeddings for user message
    chunks = embedding_service.chunk_text(message.content)
    for i, chunk in enumerate(chunks):
        embedding = embedding_service.embed_text(chunk)
        msg_embedding = MessageEmbedding(
            message_id=user_msg.id,
            embedding=embedding.tolist(),
            chunk_index=i,
            chunk_text=chunk
        )
        db.add(msg_embedding)
    
    # Check memory for similar questions and context
    memory_context = memory_manager.get_relevant_context(
        query=message.content,
        db=db,
        conversation_id=message.conversation_id,
        user_id=conversation.user_id
    )
    
    # If duplicate question found, use previous answer
    if memory_context['is_duplicate']:
        assistant_content = memory_manager.format_response_with_memory(
            query=message.content,
            memory_context=memory_context,
            ollama_service=ollama_service,
            model=message.model
        )
        is_duplicate = True
        memory_used = True
    else:
        # Get conversation history
        history = db.query(Message).filter(
            Message.conversation_id == message.conversation_id
        ).order_by(Message.created_at).limit(10).all()
        
        # Build messages for Ollama
        messages = []
        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add memory context if available
        if memory_context['suggested_context']:
            messages.append({
                "role": "system",
                "content": memory_context['suggested_context']
            })
        
        messages.append({
            "role": "user",
            "content": message.content
        })
        
        # Get cached context if available
        context = cache_service.get_context(message.conversation_id)
        
        # Generate response
        try:
            response = ollama_service.chat(
                model=message.model,
                messages=messages,
                temperature=message.temperature
            )
            
            assistant_content = response["message"]["content"]
            
            # Save context for next request
            if "context" in response:
                cache_service.set_context(message.conversation_id, response["context"])
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
        
        is_duplicate = False
        memory_used = bool(memory_context['relevant_memories'])
    
    # Define context for response
    context = cache_service.get_context(message.conversation_id)
    
    # Save assistant message
    assistant_msg = Message(
        conversation_id=message.conversation_id,
        role="assistant",
        content=assistant_content,
        token_count=len(assistant_content.split())
    )
    db.add(assistant_msg)
    db.flush()  # Flush to get the ID
    
    # Generate embeddings for assistant message
    chunks = embedding_service.chunk_text(assistant_content)
    for i, chunk in enumerate(chunks):
        embedding = embedding_service.embed_text(chunk)
        msg_embedding = MessageEmbedding(
            message_id=assistant_msg.id,
            embedding=embedding.tolist(),
            chunk_index=i,
            chunk_text=chunk
        )
        db.add(msg_embedding)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    
    return ChatResponse(
        user_message=MessageResponse.from_orm(user_msg),
        assistant_message=MessageResponse.from_orm(assistant_msg),
        context_used=context is not None,
        memory_used=memory_used,
        is_duplicate=is_duplicate
    )

@router.get("/conversation/{conversation_id}", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all messages in a conversation"""
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).offset(skip).limit(limit).all()
    
    return [MessageResponse.from_orm(msg) for msg in messages]

class SimpleChatRequest(BaseModel):
    content: str
    user_id: str = "default-user"
    model: str = "llama3.2"
    temperature: float = 0.7

class SimpleChatResponse(BaseModel):
    response: str
    conversation_id: str
    
@router.post("/simple-chat", response_model=SimpleChatResponse)
def simple_chat(
    request: SimpleChatRequest,
    db: Session = Depends(get_db)
):
    """Simple chat endpoint that auto-creates conversations"""
    # Try to find an active conversation for this user
    conversation = db.query(Conversation).filter(
        Conversation.user_id == request.user_id
    ).order_by(Conversation.updated_at.desc()).first()
    
    # Create new conversation if none exists or last one is old
    if not conversation:
        conversation = Conversation(
            user_id=request.user_id,
            title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            meta_data={"auto_created": True}
        )
        db.add(conversation)
        db.flush()
    
    # Use existing chat logic
    message = MessageCreate(
        conversation_id=conversation.id,
        content=request.content,
        model=request.model,
        temperature=request.temperature
    )
    
    # Call the existing chat function
    chat_response = chat(message, db)
    
    return SimpleChatResponse(
        response=chat_response.assistant_message.content,
        conversation_id=conversation.id
    )

@router.get("/search/{conversation_id}")
def search_messages(
    conversation_id: str,
    query: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Search messages using semantic similarity"""
    # Generate embedding for query
    query_embedding = embedding_service.embed_text(query)
    
    # Search using pgvector
    results = db.query(
        MessageEmbedding,
        MessageEmbedding.embedding.cosine_distance(query_embedding).label("distance")
    ).join(
        Message
    ).filter(
        Message.conversation_id == conversation_id
    ).order_by("distance").limit(limit).all()
    
    response = []
    for embedding, distance in results:
        response.append({
            "message_id": embedding.message_id,
            "chunk_text": embedding.chunk_text,
            "similarity": 1 - distance,
            "role": embedding.message.role,
            "created_at": embedding.message.created_at
        })
    
    return response