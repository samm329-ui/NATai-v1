import os
import uvicorn

if __name__ == "__main__":
    print("==================================================")
    print("Starting N.A.T. AI Assistant (Natasha)...")
    print("==================================================")
    
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Host: {host}, Port: {port}, Reload: {reload}")
    
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)