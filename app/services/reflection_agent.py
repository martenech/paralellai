from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
from datetime import datetime, timezone, timedelta
import re

from app.db import Conversation, Message, ConversationSummary, MetaInsight
from app.services import OllamaService, EmbeddingService

class ReflectionAgent:
    def __init__(self, 
                 ollama_service: OllamaService,
                 embedding_service: EmbeddingService,
                 model: str = "llama3.2",
                 min_messages_for_summary: int = 5):
        """
        Reflection Agent that analyzes conversations and creates meta-records
        
        Args:
            ollama_service: Service for LLM operations
            embedding_service: Service for generating embeddings
            model: LLM model to use for analysis
            min_messages_for_summary: Minimum messages before summarizing
        """
        self.ollama = ollama_service
        self.embeddings = embedding_service
        self.model = model
        self.min_messages = min_messages_for_summary
    
    def process_conversation(self, conversation_id: str, db: Session) -> Optional[ConversationSummary]:
        """
        Process a single conversation and create/update its summary
        """
        # Get conversation with messages
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return None
        
        # Get all messages
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        if len(messages) < self.min_messages:
            return None
        
        # Check if summary exists
        summary = db.query(ConversationSummary).filter(
            ConversationSummary.conversation_id == conversation_id
        ).first()
        
        # Check if we need to update (new messages since last summary)
        last_message = messages[-1]
        if summary and summary.last_message_id == last_message.id:
            return summary  # No new messages
        
        # Generate summary using LLM
        conversation_text = self._format_conversation(messages)
        
        # Create prompts for different analyses
        summary_prompt = f"""Analyze this conversation and provide:
1. A concise summary (2-3 sentences)
2. Key points discussed (list 3-5 main topics)
3. Any goals or intentions expressed by the user
4. Overall sentiment (positive/neutral/negative)

Conversation:
{conversation_text}

Respond in JSON format:
{{
    "summary": "...",
    "key_points": ["point1", "point2", ...],
    "goals": ["goal1", "goal2", ...],
    "sentiment": "positive/neutral/negative"
}}"""
        
        response = self.ollama.generate(
            model=self.model,
            prompt=summary_prompt,
            temperature=0.3  # Lower temperature for more consistent analysis
        )
        
        # Parse response
        try:
            analysis = self._parse_json_response(response['response'])
        except Exception as e:
            print(f"Error parsing reflection response: {e}")
            # Fallback to basic analysis
            analysis = {
                "summary": self._basic_summary(messages),
                "key_points": self._extract_topics(conversation_text),
                "goals": [],
                "sentiment": "neutral"
            }
        
        # Extract topics from conversation
        topics = self._extract_topics_advanced(messages)
        
        # Create or update summary
        if not summary:
            summary = ConversationSummary(
                conversation_id=conversation_id
            )
            db.add(summary)
        
        summary.summary = analysis.get("summary", "")
        summary.key_points = analysis.get("key_points", [])
        summary.topics = topics
        summary.goals = analysis.get("goals", [])
        summary.sentiment = analysis.get("sentiment", "neutral")
        summary.last_message_id = last_message.id
        summary.message_count = len(messages)
        summary.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        return summary
    
    def extract_user_insights(self, user_id: str, db: Session) -> List[MetaInsight]:
        """
        Extract high-level insights about a user from all their conversations
        """
        # Get all user conversations with summaries
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).join(ConversationSummary).all()
        
        if not conversations:
            return []
        
        insights = []
        
        # 1. Extract patterns from summaries
        all_topics = []
        all_goals = []
        sentiments = []
        
        for conv in conversations:
            if conv.summary:
                all_topics.extend(conv.summary.topics)
                all_goals.extend(conv.summary.goals)
                sentiments.append(conv.summary.sentiment)
        
        # Analyze patterns
        topic_patterns = self._find_patterns(all_topics, "interests")
        goal_patterns = self._find_patterns(all_goals, "goals")
        
        # 2. Generate user profile insights
        if topic_patterns:
            insight = MetaInsight(
                user_id=user_id,
                insight_type="interest",
                content=f"User frequently discusses: {', '.join(topic_patterns[:3])}",
                confidence=0.8,
                evidence=[{"topics": topic_patterns}]
            )
            # Generate embedding for searchability
            insight.embedding = self.embeddings.embed_text(insight.content).tolist()
            insights.append(insight)
            db.add(insight)
        
        if goal_patterns:
            insight = MetaInsight(
                user_id=user_id,
                insight_type="goal",
                content=f"User's main objectives include: {', '.join(goal_patterns[:3])}",
                confidence=0.7,
                evidence=[{"goals": goal_patterns}]
            )
            insight.embedding = self.embeddings.embed_text(insight.content).tolist()
            insights.append(insight)
            db.add(insight)
        
        # 3. Sentiment analysis
        if sentiments:
            sentiment_counts = {s: sentiments.count(s) for s in set(sentiments)}
            dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get)
            
            insight = MetaInsight(
                user_id=user_id,
                insight_type="pattern",
                content=f"User's conversations are predominantly {dominant_sentiment} in tone",
                confidence=sentiment_counts[dominant_sentiment] / len(sentiments),
                evidence=[{"sentiment_distribution": sentiment_counts}]
            )
            insight.embedding = self.embeddings.embed_text(insight.content).tolist()
            insights.append(insight)
            db.add(insight)
        
        db.commit()
        return insights
    
    def _format_conversation(self, messages: List[Message]) -> str:
        """Format messages for LLM analysis"""
        lines = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)
    
    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response"""
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(response)
    
    def _basic_summary(self, messages: List[Message]) -> str:
        """Create basic summary without LLM"""
        user_messages = [m.content for m in messages if m.role == "user"]
        if user_messages:
            return f"Conversation with {len(messages)} messages about: {user_messages[0][:100]}..."
        return f"Conversation with {len(messages)} messages"
    
    def _extract_topics(self, text: str) -> List[str]:
        """Basic topic extraction"""
        # Simple keyword extraction - in production, use better NLP
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'is', 'are', 'was', 'were'}
        words = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Count frequencies
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top topics
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:5]]
    
    def _extract_topics_advanced(self, messages: List[Message]) -> List[str]:
        """Extract topics using message content analysis"""
        all_topics = []
        for msg in messages:
            if msg.role == "user":
                topics = self._extract_topics(msg.content)
                all_topics.extend(topics)
        
        # Deduplicate and return most common
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, _ in sorted_topics[:5]]
    
    def _find_patterns(self, items: List[str], pattern_type: str) -> List[str]:
        """Find recurring patterns in lists"""
        if not items:
            return []
        
        # Count occurrences
        item_counts = {}
        for item in items:
            item_lower = item.lower().strip()
            if item_lower:
                item_counts[item_lower] = item_counts.get(item_lower, 0) + 1
        
        # Filter items that appear multiple times
        patterns = [(item, count) for item, count in item_counts.items() if count > 1]
        patterns.sort(key=lambda x: x[1], reverse=True)
        
        return [item for item, _ in patterns[:5]]