#!/usr/bin/env python3
"""
PRAMAAN Medico-Legal Evidence Platform
Local Development Runner
"""
import os
import sys
import uvicorn

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"🚀 Starting PRAMAAN Medico-Legal Evidence Platform on http://localhost:{port}")
    uvicorn.run("backend.app:app", host=host, port=port, reload=True)
