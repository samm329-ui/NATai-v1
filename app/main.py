"""
N.A.T. AI Assistant v1 - FastAPI Application
Main entry point for the API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import config
from app.models import ChatRequest, ChatResponse, SystemStatus, VectorStoreStatus
from app.services.chat_service import chat_service
from app.services.vector_store import vector_store_service
from app.services.groq_service import groq_service
from app.services.realtime_service import realtime_service
from app.utils.time_info import get_current_datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    print("\n" + "="*50)
    print(f"N.A.T. AI Assistant v1.0")
    print(f"Full Name: Natasha")
    print("="*50)
    
    print("\n[System] Initializing vector store...")
    vector_store_service.load_or_create_vectorstore()
    vector_store_service.add_learning_files()
    
    print("\n[System] System ready!")
    print(f"  Model: {config.GROQ_MODEL}")
    print(f"  Groq API: {'Available' if groq_service.is_available() else 'Not configured'}")
    print(f"  Web Search: {'Available' if realtime_service.is_available() else 'Not configured'}")
    print(f"  Learning files: {config.LEARNING_DATA_PATH}")
    print("="*50 + "\n")
    
    yield
    
    print("\n[System] Shutting down...")

app = FastAPI(
    title="N.A.T. AI Assistant v1",
    description="Advanced AI Assistant with memory and real-time search - Full Name: Natasha",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "N.A.T. AI Assistant v1",
        "full_name": "Natasha",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/chat",
            "system": "/system/status",
            "vectorstore": "/vectorstore/status",
            "sessions": "/sessions"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": get_current_datetime()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session = chat_service.get_or_create_session(
            request.session_id, 
            request.chat_type
        )
        
        chat_service.add_message(session.session_id, "user", request.message)
        history = chat_service.get_conversation_history(session.session_id)
        
        response_text = ""
        sources = None
        
        if request.chat_type == "realtime":
            result = realtime_service.chat(request.message, history)
            response_text = result["response"]
            if result.get("sources"):
                sources = result["sources"]
        else:
            context = vector_store_service.get_relevant_context(request.message)
            response_text = groq_service.chat_with_context(
                request.message, 
                context, 
                history
            )
        
        chat_service.add_message(session.session_id, "assistant", response_text)
        chat_service.save_session(session.session_id)
        
        return ChatResponse(
            response=response_text,
            session_id=session.session_id,
            chat_type=request.chat_type,
            sources=sources
        )
        
    except Exception as e:
        print(f"[API] Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/status", response_model=SystemStatus)
async def system_status():
    vector_status = vector_store_service.get_status()
    
    return SystemStatus(
        vector_store=VectorStoreStatus(
            loaded=vector_status["loaded"],
            document_count=vector_status["document_count"],
            sources=[]
        ),
        groq_available=groq_service.is_available(),
        search_available=realtime_service.is_available(),
        model_name=config.GROQ_MODEL,
        active_sessions=len(chat_service.sessions)
    )

@app.get("/vectorstore/status")
async def vectorstore_status():
    return vector_store_service.get_status()

@app.post("/vectorstore/rebuild")
async def rebuild_vectorstore():
    result = vector_store_service.add_learning_files()
    return result

@app.get("/sessions")
async def list_sessions():
    return chat_service.list_sessions()

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.session_id,
        "chat_type": session.chat_type,
        "message_count": len(session.messages),
        "messages": [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp.isoformat()}
            for msg in session.messages
        ]
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    success = chat_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}

@app.get("/learning/files")
async def list_learning_files():
    files = []
    for file_path in config.LEARNING_DATA_PATH.glob("*.txt"):
        files.append({
            "name": file_path.name,
            "size": file_path.stat().st_size
        })
    return files
