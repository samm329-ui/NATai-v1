"""
N.A.T. AI Assistant v2 - FastAPI Application
Advanced Business Intelligence Engine with Memory, Real-time Search & Streaming TTS
"""
import asyncio
import json
import base64
import os
import tempfile
import requests
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime
from pydantic import BaseModel
from pydantic import BaseModel

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

import edge_tts

from config import config
from app.models import ChatRequest, ChatResponse, SystemStatus, VectorStoreStatus, DetailedSystemStatus
from app.services.chat_service import chat_service
from app.services.vector_store import vector_store_service
from app.services.groq_service import groq_service
from app.services.realtime_service import realtime_service
from app.services.intelligence_service import intelligence_service
from app.services.memory_service import memory_service
from app.utils.time_info import get_current_datetime

# Startup time for uptime tracking
startup_time = datetime.now()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*50)
    print(f"N.A.T. AI Assistant v2.0")
    print(f"Full Name: Natasha")
    print(f"Streaming & TTS Engine Active")
    print("="*50)
    
    print("\n[System] Vector store: Lazy loading (loads on first request)")
    
    print("\n[System] System ready!")
    print(f"  Model: {config.GROQ_MODEL}")
    print(f"  Groq API: {'Available' if groq_service.is_available() else 'Not configured'}")
    print(f"  Web Search (Tavily): {'Available' if getattr(config, 'TAVILY_API_KEY', None) else 'Not configured'}")
    print(f"  Alpha Vantage: {'Available' if getattr(config, 'ALPHA_VANTAGE_KEY', None) else 'Not configured'}")
    print(f"  FMP: {'Available' if getattr(config, 'FMP_KEY', None) else 'Not configured'}")
    print(f"  News API: {'Available' if getattr(config, 'NEWS_API_KEY', None) else 'Not configured'}")
    print(f"  Google Search: {'Available' if getattr(config, 'GOOGLE_API_KEY', None) else 'Not configured'}")
    print(f"  Learning files: {config.LEARNING_DATA_PATH}")
    print("="*50 + "\n")
    
    yield
    
    print("\n[System] Shutting down...")

app = FastAPI(
    title="N.A.T. AI Assistant v2",
    description="Advanced AI Assistant with Business Intelligence - Full Name: Natasha",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# --- NEW TTS GENERATOR FUNCTION ---
async def generate_tts_audio(text: str) -> str:
    """Generates TTS audio and returns it as a base64 string."""
    if not text or not text.strip():
        return ""
    try:
        voice = getattr(config, 'TTS_VOICE', 'en-GB-RyanNeural')
        rate = getattr(config, 'TTS_RATE', '+0%')
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_path = tmp_file.name
        
        await communicate.save(tmp_path)
        
        with open(tmp_path, "rb") as audio_file:
            encoded_audio = base64.b64encode(audio_file.read()).decode("utf-8")
            
        os.remove(tmp_path)
        return encoded_audio
    except Exception as e:
        print(f"[TTS Error] {e}")
        return ""

# --- NEW STREAMING GENERATOR ---
async def _stream_generator(session_id: str, message: str, chat_type: str, use_tts: bool):
    """Handles SSE streaming and background TTS chunking."""
    session = chat_service.get_or_create_session(session_id, chat_type)
    yield f"data: {json.dumps({'session_id': session.session_id, 'chunk': '', 'done': False})}\n\n"
    
    chat_service.add_message(session.session_id, "user", message)
    history = chat_service.get_conversation_history(session.session_id)
    
    full_response = ""
    sentence_buffer = ""
    
    try:
        # We will use the stream method which we will add to the services next
        if chat_type == "realtime":
            response_stream = realtime_service.stream_chat(message, history)
        else:
            response_stream = groq_service.stream_chat_with_context(message, vector_store_service.get_relevant_context(message), history)

        for chunk_text in response_stream:
            if chunk_text:
                full_response += chunk_text
                sentence_buffer += chunk_text
                
                # Yield text chunk to frontend instantly
                yield f"data: {json.dumps({'chunk': chunk_text, 'done': False})}\n\n"
                
                # Check for sentence end for TTS
                if use_tts and any(punct in sentence_buffer for punct in ['. ', '! ', '? ', '\n']):
                    # Split at the first punctuation mark
                    for punct in ['. ', '! ', '? ', '\n']:
                        if punct in sentence_buffer:
                            parts = sentence_buffer.split(punct, 1)
                            sentence_to_speak = parts[0] + punct.strip()
                            sentence_buffer = parts[1]
                            
                            # Only generate audio if the sentence has actual letters/numbers
                            if len(sentence_to_speak.strip()) > 1:
                                audio_b64 = await generate_tts_audio(sentence_to_speak)
                                if audio_b64:
                                    yield f"data: {json.dumps({'audio': audio_b64, 'sentence': sentence_to_speak, 'done': False})}\n\n"
                            break

        # Process any remaining text in buffer for TTS
        if use_tts and len(sentence_buffer.strip()) > 1:
            audio_b64 = await generate_tts_audio(sentence_buffer)
            if audio_b64:
                yield f"data: {json.dumps({'audio': audio_b64, 'sentence': sentence_buffer, 'done': False})}\n\n"

        # Save session
        chat_service.add_message(session.session_id, "assistant", full_response)
        chat_service.save_session(session.session_id)
        
        # Extract and save persistent memories
        memory_service.extract_and_save_memory(message, full_response)
        
    except Exception as e:
        print(f"[Stream Error] {e}")
        yield f"data: {json.dumps({'chunk': f' Error: {str(e)}', 'done': True, 'session_id': session.session_id})}\n\n"
        return

    yield f"data: {json.dumps({'chunk': '', 'done': True, 'session_id': session.session_id})}\n\n"


# --- EXISTING ENDPOINTS ---

@app.get("/")
async def root():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {
        "name": "N.A.T. AI Assistant v2",
        "full_name": "Natasha",
        "version": "2.0.0",
        "status": "running",
        "engine": "Advanced Business Intelligence + Streaming",
        "endpoints": {
            "chat": "/chat",
            "chat_stream": "/chat/stream",
            "intelligence": "/intelligence",
            "system": "/system/status",
            "detailed_status": "/system/detailed",
            "vectorstore": "/vectorstore/status",
            "sessions": "/sessions"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": get_current_datetime(),
        "uptime_seconds": (datetime.now() - startup_time).total_seconds()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Standard non-streaming chat fallback
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
        elif request.chat_type == "intelligence":
            result = intelligence_service.analyze(request.message, history)
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

# --- NEW STREAMING ENDPOINTS ---

@app.post("/chat/stream")
async def chat_stream(request: Request):
    """General chat streaming endpoint"""
    data = await request.json()
    message = data.get("message", "")
    session_id = data.get("session_id")
    use_tts = data.get("tts", False)
    
    return StreamingResponse(
        _stream_generator(session_id, message, "general", use_tts),
        media_type="text/event-stream"
    )

# --- THE NEW UNIVERSAL WHISPER API ENGINE ---
@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()
        keys = getattr(config, 'GROQ_API_KEYS', [])
        api_key = keys[0] if keys else getattr(config, 'GROQ_API_KEY', '')
        
        if not api_key: return {"text": "", "error": "Groq API key missing"}

        print(f"[Speech] Sending {audio.filename} to Groq Whisper AI...")
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {"file": (audio.filename, audio_bytes, audio.content_type)}
        data = {"model": "whisper-large-v3", "response_format": "json"}
        
        response = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            return {"text": response.json().get("text", "").strip()}
        else:
            return {"text": "", "error": f"Groq Error: {response.text}"}
            
    except Exception as e:
        print(f"[Speech Error] {e}")
        return {"text": "", "error": str(e)}

@app.post("/chat/realtime/stream")
async def chat_realtime_stream(request: Request):
    """Realtime search chat streaming endpoint"""
    data = await request.json()
    message = data.get("message", "")
    session_id = data.get("session_id")
    use_tts = data.get("tts", False)
    
    return StreamingResponse(
        _stream_generator(session_id, message, "realtime", use_tts),
        media_type="text/event-stream"
    )

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

@app.get("/system/detailed", response_model=DetailedSystemStatus)
async def detailed_system_status():
    """Detailed system status with all API configurations and timestamps"""
    vector_status = vector_store_service.get_status()
    
    api_sources = []
    if getattr(config, 'GROQ_API_KEYS', None):
        api_sources.append("groq")
    if getattr(config, 'TAVILY_API_KEY', None):
        api_sources.append("tavily")
    if getattr(config, 'ALPHA_VANTAGE_KEY', None):
        api_sources.append("alpha_vantage")
    if getattr(config, 'FMP_KEY', None):
        api_sources.append("fmp")
    if getattr(config, 'NEWS_API_KEY', None):
        api_sources.append("news_api")
    if getattr(config, 'GOOGLE_API_KEY', None) and getattr(config, 'GOOGLE_CSE_ID', None):
        api_sources.append("google_search")
    if getattr(config, 'SERPAPI_KEY', None):
        api_sources.append("serpapi")
    
    cache_info = {
        "entries": len(intelligence_service.cache),
        "ttl_seconds": intelligence_service.cache_ttl
    }
    
    return DetailedSystemStatus(
        name="N.A.T.",
        full_name="Natasha",
        version="2.0.0",
        status="running",
        uptime_start=startup_time.strftime("%Y-%m-%d %H:%M:%S"),
        current_time=get_current_datetime(),
        model=config.GROQ_MODEL,
        groq_api="Available" if groq_service.is_available() else "Not configured",
        tavily_search="Available" if getattr(config, 'TAVILY_API_KEY', None) else "Not configured",
        alpha_vantage="Available" if getattr(config, 'ALPHA_VANTAGE_KEY', None) else "Not configured",
        fmp_data="Available" if getattr(config, 'FMP_KEY', None) else "Not configured",
        news_api="Available" if getattr(config, 'NEWS_API_KEY', None) else "Not configured",
        google_search="Available" if (getattr(config, 'GOOGLE_API_KEY', None) and getattr(config, 'GOOGLE_CSE_ID', None)) else "Not configured",
        vector_store={
            "loaded": vector_status["loaded"],
            "document_count": vector_status["document_count"],
            "model": vector_status.get("model", "N/A"),
            "path": str(vector_status.get("path", ""))
        },
        cache_status=cache_info,
        active_sessions=len(chat_service.sessions),
        endpoints={
            "chat": "/chat",
            "chat_stream": "/chat/stream",
            "intelligence": "/intelligence",
            "system": "/system/status",
            "detailed": "/system/detailed",
            "vectorstore": "/vectorstore/status",
            "sessions": "/sessions",
            "health": "/health"
        },
        api_sources_configured=api_sources
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

# PERSISTENT MEMORY ENDPOINTS
@app.get("/memory")
async def get_memories():
    """Get all persistent memories."""
    return {
        "memories": memory_service.get_all_memories(),
        "count": len(memory_service.memories)
    }

class MemoryRequestModel(BaseModel):
    content: str
    category: str = "general"
    importance: int = 5

@app.post("/memory")
async def add_memory(request: MemoryRequestModel):
    """Add a new persistent memory."""
    memory = memory_service.add_memory(
        content=request.content,
        category=request.category,
        importance=request.importance
    )
    return {"success": True, "memory": memory}

@app.delete("/memory/{memory_id}")
async def delete_memory(memory_id: int):
    """Delete a memory by ID."""
    memory_service.delete_memory(memory_id)
    return {"success": True, "deleted_id": memory_id}

# INTELLIGENCE ENDPOINT

class IntelligenceRequestModel(BaseModel):
    query: str
    force_refresh: bool = False

@app.post("/intelligence")
async def intelligence(request: IntelligenceRequestModel):
    """
    Analyze any company, industry, brand, or sector.
    Auto-classifies input — no manual tagging needed.
    Returns structured financial + market intelligence.
    """
    try:
        if request.force_refresh:
            key = request.query.lower().strip()
            if key in intelligence_service.cache:
                del intelligence_service.cache[key]

        result = intelligence_service.analyze(request.query)
        return {
            "success": True,
            "query": request.query,
            "entity_name": result.get("entity_name", request.query),
            "entity_type": result.get("entity_type", "unknown"),
            "classification": result.get("classification", {}),
            "structured_data": result.get("structured_data", {}),
            "response": result.get("response", ""),
            "sources_searched": result.get("sources_searched", 0),
            "api_sources_used": result.get("api_sources_used", []),
            "cached": result.get("cached", False),
            "timestamp": get_current_datetime(),
        }
    except Exception as e:
        print(f"[API] Intelligence error: {e}")
        raise HTTPException(status_code=500, detail=str(e))