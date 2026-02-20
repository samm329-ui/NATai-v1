"""
NAT Configuration Module
Loads environment variables and provides configuration settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    # Groq API Keys (supports multiple for rate limit rotation)
    GROQ_API_KEYS = [
        os.getenv("GROQ_API_KEY_1", ""),
        os.getenv("GROQ_API_KEY_2", ""),
        os.getenv("GROQ_API_KEY_3", ""),
        os.getenv("GROQ_API_KEY_4", ""),
        os.getenv("GROQ_API_KEY_5", ""),
        os.getenv("GROQ_API_KEY_6", ""),
    ]
    GROQ_API_KEYS = [key for key in GROQ_API_KEYS if key]
    
    @property
    def GROQ_API_KEY(self):
        return self.GROQ_API_KEYS[0] if self.GROQ_API_KEYS else ""
    
    # Model Configuration
    GROQ_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    
    # Search API
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
    
    # User Configuration
    YOUR_NAME = os.getenv("YOUR_NAME", "Jishu")
    ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "N.A.T.")
    
    # Paths
    BASE_DIR = BASE_DIR
    LEARNING_DATA_PATH = BASE_DIR / os.getenv("LEARNING_DATA_PATH", "database/learning_data")
    CHATS_PATH = BASE_DIR / os.getenv("CHATS_PATH", "database/chats_data")
    VECTOR_STORE_PATH = BASE_DIR / os.getenv("VECTOR_STORE_PATH", "database/vector_store")
    
    # Embedding Model
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    # Create directories if they don't exist
    @classmethod
    def init_paths(cls):
        cls.LEARNING_DATA_PATH.mkdir(parents=True, exist_ok=True)
        cls.CHATS_PATH.mkdir(parents=True, exist_ok=True)
        cls.VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

# Initialize paths
Config.init_paths()

# Export singleton
config = Config()
