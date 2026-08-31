"""
PRAMAAN Medico-Legal Evidence Platform
Root Application Shim (routes to backend.app)
"""
from backend.app import app, templates, _find_dir, get_current_role

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
