"""
API routes for customer support agent
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ..agent import (
    TicketRouter,
    SupportChatbot,
    KnowledgeBase,
    SentimentAnalyzer,
    AutoResponder
)

router = APIRouter()

# Initialize agents
ticket_router = TicketRouter()
chatbot = SupportChatbot()
kb = KnowledgeBase()
sentiment_analyzer = SentimentAnalyzer()
auto_responder = AutoResponder()

# Active WebSocket connections
active_connections: List[WebSocket] = []


# Request/Response Models
class TicketRequest(BaseModel):
    subject: str
    description: str
    customer_tier: Optional[str] = "standard"


class ChatMessage(BaseModel):
    conversation_id: str
    message: str
    language: Optional[str] = "en"


class KBArticle(BaseModel):
    title: str
    content: str
    category: Optional[str] = "general"


# Routes
@router.post("/tickets/route")
async def route_ticket(ticket: TicketRequest):
    """Route a support ticket"""
    try:
        routing = ticket_router.route_ticket(
            subject=ticket.subject,
            description=ticket.description,
            customer_tier=ticket.customer_tier
        )
        
        sla = ticket_router.suggest_sla(routing)
        routing['sla'] = sla
        
        return routing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat_message(msg: ChatMessage):
    """Send a chat message"""
    try:
        response = chatbot.chat(
            conversation_id=msg.conversation_id,
            message=msg.message,
            language=msg.language
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Process message
            response = chatbot.chat(
                conversation_id=conversation_id,
                message=data
            )
            
            # Send response
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)


@router.post("/kb/search")
async def search_knowledge_base(query: str, category: Optional[str] = None):
    """Search knowledge base"""
    try:
        results = kb.search(query, category=category)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/answer")
async def answer_question(question: str, category: Optional[str] = None):
    """Get answer from knowledge base"""
    try:
        answer = kb.answer_question(question, category=category)
        return answer
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentiment")
async def analyze_sentiment(text: str):
    """Analyze sentiment"""
    try:
        sentiment = sentiment_analyzer.analyze(text)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve")
async def suggest_resolution(description: str, category: str = "general"):
    """Suggest resolution steps"""
    try:
        resolution = auto_responder.suggest_resolution(description, category)
        return resolution
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    conversation = chatbot.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/kb/index")
async def index_articles(articles: List[KBArticle]):
    """Index knowledge base articles"""
    try:
        article_dicts = [a.dict() for a in articles]
        result = kb.index_articles(article_dicts)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
