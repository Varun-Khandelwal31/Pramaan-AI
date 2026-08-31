import sys
import os

# Ensure all possible root paths in local and serverless environments are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

for path_candidate in [parent_dir, current_dir, os.getcwd(), "/var/task", "/var/task/api"]:
    if path_candidate and path_candidate not in sys.path:
        sys.path.insert(0, path_candidate)

try:
    from backend.app import app as raw_app
except Exception as err:
    try:
        from app import app as raw_app
    except Exception as inner_err:
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Vercel Serverless: Could not load FastAPI app instance: {err} | {inner_err}")

# Pure ASGI middleware to cleanly normalize Vercel internal rewrite paths
class VercelASGINormalizer:
    def __init__(self, asgi_app):
        self.app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            headers = dict(scope.get("headers", []))
            matched_path = headers.get(b"x-matched-path", b"").decode("utf-8", errors="ignore")
            forwarded_uri = headers.get(b"x-forwarded-uri", b"").decode("utf-8", errors="ignore")

            if matched_path and not matched_path.startswith("/api/index"):
                scope["path"] = matched_path
            elif forwarded_uri and not forwarded_uri.startswith("/api/index"):
                scope["path"] = forwarded_uri.split("?")[0]
            elif path.startswith("/api/index.py"):
                new_path = path[len("/api/index.py"):]
                scope["path"] = new_path if new_path.startswith("/") else ("/" + new_path)
            elif path.startswith("/api/index"):
                new_path = path[len("/api/index"):]
                scope["path"] = new_path if new_path.startswith("/") else ("/" + new_path)

        await self.app(scope, receive, send)

# Top-level ASGI app instance for Vercel
app = VercelASGINormalizer(raw_app)
