"""
Vercel Serverless Entry Point — exposes the FastAPI app as a handler.
"""
import sys
import os

# Add the project root to sys.path so we can import main, config, etc.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from main import app
except Exception as e:
    # If import fails, create a minimal app that shows the error
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/{path:path}")
    async def error_handler(path: str = ""):
        return {
            "error": "Failed to import main app",
            "detail": str(e),
            "type": type(e).__name__,
            "project_root": PROJECT_ROOT,
            "sys_path": sys.path[:5],
            "cwd": os.getcwd(),
            "files_in_root": os.listdir(PROJECT_ROOT) if os.path.exists(PROJECT_ROOT) else "ROOT NOT FOUND",
        }
