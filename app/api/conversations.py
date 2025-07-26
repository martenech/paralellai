from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db, Conversation, Message
from app.services import CacheService

router = APIRouter()
cache_service = CacheService()

class ConversationCreate(BaseModel):
    user_id: str
    title: Optional[str] = None
    meta_data: Optional[dict] = {}

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    meta_data: dict
    message_count: int = 0

    class Config:
        from_attributes = True

@router.post("/", response_model=ConversationResponse)
def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    db_conversation = Conversation(
        user_id=conversation.user_id,
        title=conversation.title,
        meta_data=conversation.meta_data
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    response = ConversationResponse.from_orm(db_conversation)
    response.message_count = 0
    return response

@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    message_count = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()
    
    response = ConversationResponse.from_orm(conversation)
    response.message_count = message_count
    return response

@router.get("/user/{user_id}", response_model=List[ConversationResponse])
def get_user_conversations(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all conversations for a user"""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).offset(skip).limit(limit).all()
    
    responses = []
    for conv in conversations:
        message_count = len(conv.messages)
        response = ConversationResponse.from_orm(conv)
        response.message_count = message_count
        responses.append(response)
    
    return responses

@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Delete cached context
    cache_service.delete_context(conversation_id)
    
    # Delete conversation (messages will cascade)
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}