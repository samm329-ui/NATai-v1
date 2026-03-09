import json
import os
import webbrowser
from app.services.groq_service import groq_service

class SmartActionEngine:
    def __init__(self):
        self.local_mappings = {
            "Doctor Drift": "C:\\Users\\jishu\\DoctorDrift",  # Ensure this points to a valid dir or adjust accordingly
            "Protein Zone": "C:\\Users\\jishu\\ProteinZone"   # Defaulting to user's home or a standard path
        }
    
    def evaluate_and_execute(self, user_message: str):
        """
        Calls Groq to classify the intent in a strict JSON format.
        If it's an action, performs it and returns a confirmation string.
        Otherwise, returns None to continue normal chat flow.
        """
        system_prompt = '''You are a strict JSON command router for a local AI assistant.
Analyze the user's input and classify their intent into one of these actions:
- "open_web": For opening websites (e.g. "open youtube", "go to facebook"). Map target to a full URL (https://www.youtube.com).
- "open_local": For opening local projects/apps (e.g. "open Doctor Drift", "launch Protein Zone"). Map target to the exact app name.
- "chat": For standard conversational queries or questions.

You MUST respond with purely JSON (no markdown block, just raw JSON). Example:
{"action": "open_web", "target": "https://www.google.com"}
'''
        
        try:
            print(f"\n[SmartActionEngine] Analyzing input: '{user_message}'")
            response = groq_service.chat(
                message=user_message,
                system_prompt=system_prompt,
                history=[]
            )
            print(f"[SmartActionEngine] Raw LLM Response: {response}")
            
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                clean_json = json_match.group(0)
            else:
                # Clean up the response if the LLM hallucinated markdown code blocks
                clean_json = response.replace("```json", "").replace("```", "").strip()
                
            data = json.loads(clean_json)
            print(f"[SmartActionEngine] Parsed JSON: {data}")
            
            action = data.get("action")
            target = data.get("target")
            
            if action == "open_web" and target:
                webbrowser.open(target)
                return f"Opening web portal for {target}..."
                
            elif action == "open_local" and target:
                # Find matching target path (case-insensitive)
                matched_target = None
                for key in self.local_mappings.keys():
                    if key.lower() in target.lower() or target.lower() in key.lower():
                        matched_target = key
                        break
                
                path = self.local_mappings.get(matched_target) if matched_target else target
                
                # Default "start" for Windows
                os.system(f'start "" "{path}"')
                return f"Launching local application: {matched_target or target}."
                
            elif action == "chat":
                return None
                
        except Exception as e:
            print(f"SmartActionEngine Error: {e}")
            return None
            
        return None

action_engine = SmartActionEngine()
