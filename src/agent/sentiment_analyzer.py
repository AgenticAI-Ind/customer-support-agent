"""
Sentiment analysis for customer support interactions
"""

import logging
from typing import Dict, List
import re

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment in customer communications"""

    def __init__(self, use_transformer: bool = True):
        """
        Initialize sentiment analyzer

        Args:
            use_transformer: Use transformer model for analysis
        """
        self.use_transformer = use_transformer
        self.sentiment_pipeline = None

        if use_transformer:
            try:
                from transformers import pipeline
                self.sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english"
                )
                logger.info("Loaded transformer sentiment model")
            except Exception as e:
                logger.warning(f"Could not load transformer: {e}")
                self.use_transformer = False

    def analyze(self, text: str) -> Dict:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze

        Returns:
            Dict with sentiment analysis results
        """
        try:
            # Get sentiment
            if self.use_transformer and self.sentiment_pipeline:
                result = self.sentiment_pipeline(text[:512])[0]
                sentiment = result['label'].lower()
                confidence = result['score']
            else:
                sentiment, confidence = self._keyword_sentiment(text)

            # Detect emotions
            emotions = self._detect_emotions(text)

            # Detect urgency
            urgency = self._detect_urgency(text)

            # Detect frustration level
            frustration = self._detect_frustration(text)

            return {
                "sentiment": sentiment,  # positive, negative, neutral
                "confidence": confidence,
                "emotions": emotions,
                "urgency": urgency,
                "frustration_level": frustration,
                "requires_escalation": self._needs_escalation(
                    sentiment, emotions, urgency, frustration
                )
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "error": str(e)
            }

    def _keyword_sentiment(self, text: str) -> tuple:
        """Fallback keyword-based sentiment"""
        text_lower = text.lower()

        positive_words = [
            'thank', 'great', 'excellent', 'wonderful', 'love',
            'happy', 'satisfied', 'pleased', 'perfect', 'awesome',
            'fantastic', 'amazing', 'appreciate'
        ]

        negative_words = [
            'bad', 'terrible', 'horrible', 'awful', 'worst',
            'hate', 'disappointed', 'frustrated', 'angry', 'upset',
            'useless', 'waste', 'poor', 'unacceptable', 'pathetic'
        ]

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            return 'positive', min(0.9, 0.6 + (pos_count * 0.1))
        elif neg_count > pos_count:
            return 'negative', min(0.9, 0.6 + (neg_count * 0.1))
        else:
            return 'neutral', 0.5

    def _detect_emotions(self, text: str) -> List[str]:
        """Detect specific emotions"""
        text_lower = text.lower()
        emotions = []

        emotion_keywords = {
            "angry": ['angry', 'furious', 'mad', 'outraged', 'livid'],
            "frustrated": ['frustrated', 'annoyed', 'irritated', 'bothered'],
            "disappointed": ['disappointed', 'let down', 'expected better'],
            "confused": ['confused', 'don\\'t understand', 'unclear', 'lost'],
            "happy": ['happy', 'glad', 'pleased', 'delighted', 'satisfied'],
            "grateful": ['thank', 'grateful', 'appreciate']
        }

        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                emotions.append(emotion)

        return emotions

    def _detect_urgency(self, text: str) -> str:
        """Detect urgency level"""
        text_lower = text.lower()

        high_urgency = [
            'urgent', 'asap', 'immediately', 'emergency', 'critical',
            'right now', 'right away', 'can\\'t wait'
        ]

        medium_urgency = [
            'soon', 'quickly', 'hurry', 'important', 'need'
        ]

        # Check for caps lock (shouting)
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

        # Check for multiple exclamation marks
        exclamation_count = text.count('!')

        if any(word in text_lower for word in high_urgency) or exclamation_count >= 3 or caps_ratio > 0.5:
            return "high"
        elif any(word in text_lower for word in medium_urgency) or exclamation_count >= 1:
            return "medium"
        else:
            return "low"

    def _detect_frustration(self, text: str) -> str:
        """Detect frustration level (low, medium, high)"""
        text_lower = text.lower()

        high_frustration = [
            'this is ridiculous', 'this is unacceptable', 'i\\'ve had enough',
            'i want a refund', 'cancel my', 'speak to manager',
            'lawsuit', 'lawyer', 'sue', 'pathetic', 'worst'
        ]

        medium_frustration = [
            'frustrated', 'disappointed', 'not happy', 'expected better',
            'this is annoying', 'waste of time', 'not working'
        ]

        if any(phrase in text_lower for phrase in high_frustration):
            return "high"
        elif any(phrase in text_lower for phrase in medium_frustration):
            return "medium"
        else:
            return "low"

    def _needs_escalation(
        self,
        sentiment: str,
        emotions: List[str],
        urgency: str,
        frustration: str
    ) -> bool:
        """Determine if interaction needs escalation"""
        # High frustration always escalates
        if frustration == "high":
            return True

        # Angry + high urgency escalates
        if "angry" in emotions and urgency == "high":
            return True

        # Negative sentiment + high urgency escalates
        if sentiment == "negative" and urgency == "high":
            return True

        return False

    def analyze_conversation(self, messages: List[Dict]) -> Dict:
        """
        Analyze sentiment trend in a conversation

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Dict with conversation sentiment analysis
        """
        customer_messages = [
            m for m in messages
            if m.get('role') == 'customer'
        ]

        if not customer_messages:
            return {"status": "no_customer_messages"}

        sentiments = []
        for msg in customer_messages:
            analysis = self.analyze(msg['content'])
            sentiments.append(analysis)

        # Calculate trends
        positive_count = sum(1 for s in sentiments if s['sentiment'] == 'positive')
        negative_count = sum(1 for s in sentiments if s['sentiment'] == 'negative')

        # Sentiment getting worse?
        if len(sentiments) >= 2:
            recent_negative = sum(
                1 for s in sentiments[-2:]
                if s['sentiment'] == 'negative'
            )
            trend = "worsening" if recent_negative >= 2 else "stable"
        else:
            trend = "stable"

        return {
            "total_messages": len(customer_messages),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "trend": trend,
            "latest_sentiment": sentiments[-1] if sentiments else {},
            "needs_escalation": any(s.get('requires_escalation') for s in sentiments)
        }

    def get_response_tone(self, sentiment: Dict) -> str:
        """
        Suggest appropriate response tone based on sentiment

        Args:
            sentiment: Sentiment analysis result

        Returns:
            Recommended tone (empathetic, professional, enthusiastic, etc.)
        """
        if sentiment.get('frustration_level') == 'high':
            return "empathetic_apologetic"

        if 'angry' in sentiment.get('emotions', []):
            return "calm_professional"

        if 'confused' in sentiment.get('emotions', []):
            return "clear_helpful"

        if sentiment.get('sentiment') == 'positive':
            return "friendly_enthusiastic"

        return "professional_helpful"
