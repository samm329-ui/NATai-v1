#!/usr/bin/env python3
import os
import sys

print("STARTING...", flush=True)
print(f"PORT={os.environ.get('PORT', 'NOT_SET')}", flush=True)
print(f"PYTHON={sys.version}", flush=True)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    
    print(f"Starting uvicorn on {host}:{port} reload={reload}", flush=True)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
