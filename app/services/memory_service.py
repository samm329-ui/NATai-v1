import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from config import config


class MemoryService:
    def __init__(self):
        self.memory_file = config.MEMORY_PATH
        self.memories: List[Dict] = []
        self._load_memory()

    def _load_memory(self):
        """Load memories from the JSON file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = data.get('memories', [])
                print(f"[MemoryService] Loaded {len(self.memories)} persistent memories")
            except Exception as e:
                print(f"[MemoryService] Error loading memory: {e}")
                self.memories = []
        else:
            self.memories = []

    def _save_memory(self):
        """Save memories to the JSON file."""
        try:
            os.makedirs(self.memory_file.parent, exist_ok=True)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'memories': self.memories,
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[MemoryService] Error saving memory: {e}")

    def add_memory(self, content: str, category: str = "general", importance: int = 5):
        """Add a new persistent memory."""
        memory = {
            'id': len(self.memories) + 1,
            'content': content,
            'category': category,
            'importance': importance,
            'created_at': datetime.now().isoformat()
        }
        self.memories.append(memory)
        self._save_memory()
        print(f"[MemoryService] Added memory: {content[:50]}...")
        return memory

    def update_memory(self, memory_id: int, new_content: str):
        """Update an existing memory."""
        for mem in self.memories:
            if mem['id'] == memory_id:
                mem['content'] = new_content
                mem['updated_at'] = datetime.now().isoformat()
                self._save_memory()
                return True
        return False

    def delete_memory(self, memory_id: int):
        """Delete a memory by ID."""
        self.memories = [m for m in self.memories if m['id'] != memory_id]
        self._save_memory()

    def get_all_memories(self) -> List[Dict]:
        """Get all memories sorted by importance."""
        return sorted(self.memories, key=lambda x: x.get('importance', 0), reverse=True)

    def get_personal_info(self) -> str:
        """Get personal info formatted for system prompt."""
        personal = [m['content'] for m in self.memories if m.get('category') == 'personal']
        if personal:
            return "PERSONAL USER INFO:\n" + "\n".join([f"- {p}" for p in personal])
        return ""

    def get_system_prompt_context(self) -> str:
        """Get all memories formatted for system prompt."""
        if not self.memories:
            return ""
        
        lines = ["PERSISTENT USER MEMORIES (Always remember these):"]
        for mem in self.get_all_memories():
            lines.append(f"- {mem['content']}")
        return "\n".join(lines)

    def has_memory_keyword(self, text: str) -> bool:
        """Check if text contains commands to store memory."""
        keywords = [
            'remember that', 'remember this', 'always remember',
            'never forget', 'keep in mind', 'note that',
            'call me', 'my name is', 'i am', 'i\'m',
            'from now on', 'from today', 'always call me'
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def extract_and_save_memory(self, user_message: str, assistant_response: str = "") -> Optional[str]:
        """Extract important info from user message and save if significant."""
        text_lower = user_message.lower()
        
        # Check for explicit memory commands
        if 'call me' in text_lower:
            # Extract the name/title
            import re
            patterns = [
                r'call me (\w+)',
                r'always call me (\w+)',
                r'my name is (\w+)',
                r'i am (\w+)',
                r'i\'m (\w+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    name = match.group(1).title()
                    self.add_memory(f"User's name/title: {name}", category="personal", importance=10)
                    return f"I've noted it - I'll call you {name} from now on."
        
        # Check for preferences
        if 'prefer' in text_lower or 'like' in text_lower or 'hate' in text_lower:
            self.add_memory(f"User preference mentioned: {user_message[:100]}", category="preferences", importance=7)
            
        return None


memory_service = MemoryService()
