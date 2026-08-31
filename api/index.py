import sys
import os

# Ensure all possible root paths in local and serverless environments are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

for path_candidate in [parent_dir, current_dir, os.getcwd(), "/var/task", "/var/task/api"]:
    if path_candidate and path_candidate not in sys.path:
        sys.path.insert(0, path_candidate)

try:
    from backend.app import app
except Exception as err:
    # If standard import fails, try direct import from app
    try:
        from app import app
    except Exception as inner_err:
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Vercel Serverless: Could not load FastAPI app instance: {err} | {inner_err}")

# Explicit top-level FastAPI instance for Vercel Python runtime discovery
app = app
