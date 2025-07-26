from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db import get_db, ConversationSummary, MetaInsight
from app.services import OllamaService, OllamaEmbeddingService, ReflectionAgent
from app.config import config

router = APIRouter()

# Initialize services based on config
if config.EMBEDDING_PROVIDER == "ollama":
    embedding_service = OllamaEmbeddingService(
        model=config.EMBEDDING_MODEL
    )
else:
    from app.services import EmbeddingService
    embedding_service = EmbeddingService()

ollama_service = OllamaService()
reflection_agent = ReflectionAgent(ollama_service, embedding_service)

class ConversationSummaryResponse(BaseModel):
    id: str
    conversation_id: str
    summary: str
    key_points: List[str]
    topics: List[str]
    goals: List[str]
    sentiment: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    message_count: int

    class Config:
        from_attributes = True

class MetaInsightResponse(BaseModel):
    id: str
    user_id: str
    insight_type: str
    content: str
    confidence: float
    evidence: List[dict]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

@router.get("/conversation/{conversation_id}/summary", response_model=Optional[ConversationSummaryResponse])
def get_conversation_summary(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get summary for a specific conversation"""
    summary = db.query(ConversationSummary).filter(
        ConversationSummary.conversation_id == conversation_id
    ).first()
    
    if not summary:
        return None
    
    return ConversationSummaryResponse.from_orm(summary)

@router.post("/conversation/{conversation_id}/summarize", response_model=ConversationSummaryResponse)
def create_conversation_summary(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Manually trigger summarization for a conversation"""
    summary = reflection_agent.process_conversation(conversation_id, db)
    
    if not summary:
        raise HTTPException(
            status_code=400, 
            detail="Conversation not found or too few messages to summarize"
        )
    
    return ConversationSummaryResponse.from_orm(summary)

@router.get("/user/{user_id}/insights", response_model=List[MetaInsightResponse])
def get_user_insights(
    user_id: str,
    insight_type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get insights for a specific user"""
    query = db.query(MetaInsight).filter(
        MetaInsight.user_id == user_id
    )
    
    if insight_type:
        query = query.filter(MetaInsight.insight_type == insight_type)
    
    insights = query.order_by(
        MetaInsight.confidence.desc(),
        MetaInsight.created_at.desc()
    ).limit(limit).all()
    
    return [MetaInsightResponse.from_orm(insight) for insight in insights]

@router.post("/user/{user_id}/analyze", response_model=List[MetaInsightResponse])
def analyze_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Manually trigger user analysis to extract insights"""
    insights = reflection_agent.extract_user_insights(user_id, db)
    
    if not insights:
        raise HTTPException(
            status_code=404,
            detail="No conversations found for user or unable to extract insights"
        )
    
    return [MetaInsightResponse.from_orm(insight) for insight in insights]

@router.get("/summaries/recent", response_model=List[ConversationSummaryResponse])
def get_recent_summaries(
    user_id: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get recent conversation summaries"""
    query = db.query(ConversationSummary).join(
        ConversationSummary.conversation
    )
    
    if user_id:
        from app.db import Conversation
        query = query.filter(Conversation.user_id == user_id)
    
    summaries = query.order_by(
        ConversationSummary.updated_at.desc()
    ).limit(limit).all()
    
    return [ConversationSummaryResponse.from_orm(summary) for summary in summaries]

@router.get("/search/insights", response_model=List[MetaInsightResponse])
def search_insights(
    query: str,
    user_id: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Search insights using semantic similarity"""
    # Generate embedding for query
    query_embedding = embedding_service.embed_text(query)
    
    # Build SQL query
    from sqlalchemy import text
    
    sql = text("""
        SELECT 
            mi.*,
            1 - (mi.embedding <=> CAST(:query_embedding AS vector)) as similarity
        FROM meta_insights mi
        WHERE 
            1 - (mi.embedding <=> CAST(:query_embedding AS vector)) > 0.5
            AND (:user_id IS NULL OR mi.user_id = :user_id)
        ORDER BY similarity DESC
        LIMIT :limit
    """)
    
    results = db.execute(sql, {
        'query_embedding': query_embedding.tolist(),
        'user_id': user_id,
        'limit': limit
    }).fetchall()
    
    insights = []
    for row in results:
        insight = db.query(MetaInsight).filter(
            MetaInsight.id == row.id
        ).first()
        if insight:
            insights.append(MetaInsightResponse.from_orm(insight))
    
    return insights