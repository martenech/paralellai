from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta_data = Column(JSON, default={})
    
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    token_count = Column(Integer, default=0)
    
    conversation = relationship("Conversation", back_populates="messages")
    embeddings = relationship("MessageEmbedding", back_populates="message", cascade="all, delete-orphan")

class MessageEmbedding(Base):
    __tablename__ = "message_embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)
    embedding = Column(Vector(768))  # dimension for nomic-embed-text (configurable)
    chunk_index = Column(Integer, default=0)
    chunk_text = Column(Text)
    
    message = relationship("Message", back_populates="embeddings")

class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, unique=True)
    summary = Column(Text, nullable=False)
    key_points = Column(JSON, default=[])  # List of key points
    topics = Column(JSON, default=[])  # Extracted topics
    goals = Column(JSON, default=[])  # Identified goals
    sentiment = Column(String, nullable=True)  # Overall sentiment
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_id = Column(String, nullable=True)  # Track last processed message
    message_count = Column(Integer, default=0)
    
    conversation = relationship("Conversation", back_populates="summary")

class MetaInsight(Base):
    __tablename__ = "meta_insights"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    insight_type = Column(String, nullable=False)  # 'pattern', 'goal', 'interest', 'knowledge'
    content = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    evidence = Column(JSON, default=[])  # References to conversations/messages
    embedding = Column(Vector(768))  # For similarity search (configurable)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Add relationship to Conversation model
Conversation.summary = relationship("ConversationSummary", uselist=False, back_populates="conversation")