import time
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import config

class GroqService:
    def __init__(self):
        self.current_key_index = 0
        self.llm = None
        self.model_name = config.GROQ_MODEL
        
    def _get_next_api_key(self):
        if not config.GROQ_API_KEYS:
            raise Exception("No Groq API keys configured")
        key = config.GROQ_API_KEYS[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(config.GROQ_API_KEYS)
        return key
    
    def _create_llm(self):
        api_key = self._get_next_api_key()
        self.llm = ChatGroq(groq_api_key=api_key, model_name=self.model_name, temperature=0.7, max_tokens=2048, timeout=60)
    
    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        max_retries = len(config.GROQ_API_KEYS) if config.GROQ_API_KEYS else 1
        retries = 0
        while retries < max_retries:
            try:
                if not self.llm:
                    self._create_llm()
                lc_messages = []
                if system_prompt:
                    lc_messages.append(SystemMessage(content=system_prompt))
                for msg in messages:
                    if msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg["content"]))
                response = self.llm.invoke(lc_messages)
                return response.content
            except Exception as e:
                error_str = str(e).lower()
                if "rate_limit" in error_str or "429" in error_str:
                    print(f"[Groq] Rate limit reached, rotating to next key... ({retries + 1}/{max_retries})")
                    self.llm = None
                    retries += 1
                    time.sleep(1)
                    continue
                elif "api" in error_str or "auth" in error_str or "401" in error_str:
                    print(f"[Groq] API error: {e}, trying next key...")
                    self.llm = None
                    retries += 1
                    continue
                else:
                    raise e
        raise Exception("All Groq API keys failed")
    
    def chat_with_context(self, user_message: str, context: str, conversation_history: List[Dict[str, str]] = None) -> str:
        system_prompt = f"""You are {config.ASSISTANT_NAME}, an advanced AI assistant. Your full name is Natasha.

IMPORTANT CONTEXT FROM YOUR MEMORY:
{context}

Guidelines:
- Use the context above to answer personal questions about the user
- Be helpful, concise, and friendly
- If you don't know something, say so honestly
- Always be respectful and professional"""
        messages = conversation_history or []
        messages.append({"role": "user", "content": user_message})
        return self.chat(messages, system_prompt)
    
    def is_available(self) -> bool:
        return len(config.GROQ_API_KEYS) > 0 and config.GROQ_API_KEYS[0] != ""

groq_service = GroqService()
