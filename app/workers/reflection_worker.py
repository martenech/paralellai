import asyncio
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
import os
import logging

from app.db import Conversation, ConversationSummary, init_db
from app.services import OllamaService, EmbeddingService, ReflectionAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReflectionWorker:
    def __init__(self, 
                 database_url: str = None,
                 process_interval: int = 300,  # 5 minutes
                 batch_size: int = 10):
        """
        Background worker for reflection processing
        
        Args:
            database_url: Database connection string
            process_interval: Seconds between processing runs
            batch_size: Number of conversations to process per run
        """
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://llm_user:llm_password@postgres:5432/llm_memory"
        )
        self.process_interval = process_interval
        self.batch_size = batch_size
        
        # Initialize services
        self.ollama = OllamaService()
        self.embeddings = EmbeddingService()
        self.reflection_agent = ReflectionAgent(self.ollama, self.embeddings)
        
        # Setup database
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize database
        init_db()
        
        logger.info("ReflectionWorker initialized")
    
    async def start(self):
        """Start the worker loop"""
        logger.info("Starting reflection worker...")
        
        while True:
            try:
                await self._process_batch()
                await asyncio.sleep(self.process_interval)
            except Exception as e:
                logger.error(f"Error in reflection worker: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _process_batch(self):
        """Process a batch of conversations"""
        db = self.SessionLocal()
        try:
            # Find conversations that need processing
            # 1. Conversations without summaries
            # 2. Conversations with new messages since last summary
            
            subquery = db.query(ConversationSummary.conversation_id)
            
            # Get conversations without summaries
            new_conversations = db.query(Conversation).filter(
                ~Conversation.id.in_(subquery)
            ).limit(self.batch_size // 2).all()
            
            # Get conversations that need updates (modified in last hour)
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            updated_conversations = db.query(Conversation).join(
                ConversationSummary
            ).filter(
                and_(
                    Conversation.updated_at > one_hour_ago,
                    ConversationSummary.updated_at < Conversation.updated_at
                )
            ).limit(self.batch_size // 2).all()
            
            conversations_to_process = new_conversations + updated_conversations
            
            if not conversations_to_process:
                logger.debug("No conversations to process")
                return
            
            logger.info(f"Processing {len(conversations_to_process)} conversations")
            
            # Process each conversation
            for conversation in conversations_to_process:
                try:
                    logger.info(f"Processing conversation {conversation.id}")
                    summary = await asyncio.to_thread(
                        self.reflection_agent.process_conversation,
                        conversation.id,
                        db
                    )
                    if summary:
                        logger.info(f"Created/updated summary for conversation {conversation.id}")
                except Exception as e:
                    logger.error(f"Error processing conversation {conversation.id}: {e}")
                    continue
            
            # Extract user insights periodically (every 10th run)
            if hasattr(self, '_run_count'):
                self._run_count += 1
            else:
                self._run_count = 1
            
            if self._run_count % 10 == 0:
                await self._extract_user_insights(db)
            
        finally:
            db.close()
    
    async def _extract_user_insights(self, db):
        """Extract insights for all active users"""
        logger.info("Extracting user insights...")
        
        # Get unique user IDs from recent conversations
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_users = db.query(Conversation.user_id).filter(
            Conversation.updated_at > one_week_ago
        ).distinct().limit(10).all()
        
        for (user_id,) in active_users:
            try:
                insights = await asyncio.to_thread(
                    self.reflection_agent.extract_user_insights,
                    user_id,
                    db
                )
                if insights:
                    logger.info(f"Extracted {len(insights)} insights for user {user_id}")
            except Exception as e:
                logger.error(f"Error extracting insights for user {user_id}: {e}")
    
    def stop(self):
        """Stop the worker"""
        logger.info("Stopping reflection worker...")
        # Cleanup if needed

async def main():
    """Main entry point for the worker"""
    worker = ReflectionWorker()
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())