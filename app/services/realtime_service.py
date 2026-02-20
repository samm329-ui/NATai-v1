from typing import List, Dict, Any, Optional
from datetime import datetime
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
from config import config
from app.services.groq_service import groq_service
from app.services.vector_store import vector_store_service

class RealtimeService:
    def __init__(self):
        self.tavily_client = None
        if TAVILY_AVAILABLE and config.TAVILY_API_KEY:
            try:
                self.tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
            except Exception as e:
                print(f"[Realtime] Tavily initialization error: {e}")
    
    def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        results = []
        if self.tavily_client:
            try:
                search_results = self.tavily_client.search(query=query, max_results=max_results)
                for result in search_results.get("results", []):
                    results.append({"title": result.get("title", ""), "url": result.get("url", ""), "content": result.get("content", "")[:500], "source": "tavily"})
                return results
            except Exception as e:
                print(f"[Realtime] Tavily search error: {e}")
        print("[Realtime] Using fallback search mode")
        return results
    
    def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        print(f"[Realtime] Processing: {message[:50]}...")
        context = vector_store_service.get_relevant_context(message)
        search_results = self.search_web(message)
        search_context = ""
        if search_results:
            search_context = "\n\nRECENT WEB SEARCH RESULTS:\n"
            for i, result in enumerate(search_results, 1):
                search_context += f"\n{i}. {result['title']}\n   {result.get('content', '')[:300]}...\n   Source: {result['url']}\n"
        system_prompt = f"""You are {config.ASSISTANT_NAME}, an advanced AI assistant. Your full name is Natasha, with real-time web search capabilities.

CURRENT TIME: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

USER'S INFO (from memory):
{context}

WEB SEARCH RESULTS:
{search_context}

Guidelines:
- Use the web search results above for current information
- Always provide accurate, up-to-date information when available
- Cite sources when using web search results
- Be helpful, concise, and friendly
- If you don't know something, say so honestly"""
        messages = conversation_history or []
        messages.append({"role": "user", "content": message})
        try:
            response = groq_service.chat(messages, system_prompt)
            return {"response": response, "sources": search_results, "search_used": len(search_results) > 0}
        except Exception as e:
            print(f"[Realtime] Error: {e}")
            return {"response": f"I apologize, but I encountered an error: {str(e)}", "sources": [], "search_used": False}
    
    def is_available(self) -> bool:
        return self.tavily_client is not None or True

realtime_service = RealtimeService()
