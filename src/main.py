"""
Customer Support & Chatbot Agent
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os

from .config import settings
from .api.routes import router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Customer Support Agent...")
    os.makedirs("./data/knowledge_base", exist_ok=True)
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="Customer Support & Chatbot Agent",
    description="""Enterprise customer support with:
    - Intelligent ticket routing
    - Multi-language AI chatbot  
    - Knowledge base with RAG
    - Sentiment analysis
    - Automated resolutions
    - Real-time WebSocket chat
    
    Reduce response time by 70%.
    """,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1", tags=["Customer Support"])

@app.get("/")
async def root():
    return {
        "service": "Customer Support & Chatbot Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": ["Ticket Routing", "AI Chatbot", "Knowledge Base", "Sentiment Analysis", "Auto-Resolution", "WebSocket Chat"]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
