"""
NATai v1 Run Script
Starts the FastAPI server
"""
import uvicorn

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Starting N.A.T. AI Assistant v1...")
    print("="*50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
