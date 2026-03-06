import os
import sys
import uvicorn

if __name__ == "__main__":
    print("==================================================")
    print("Starting N.A.T. AI Assistant (Natasha)...")
    print("==================================================")
    print(f"Python version: {sys.version}")
    print(f"PORT env: {os.environ.get('PORT', 'NOT SET')}")
    
    try:
        port = int(os.environ.get("PORT", 8000))
    except (ValueError, TypeError):
        port = 8000
        print(f"Invalid PORT, using default: {port}")
    
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Host: {host}, Port: {port}, Reload: {reload}")
    sys.stdout.flush()
    
    try:
        uvicorn.run("app.main:app", host=host, port=port, reload=reload)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
