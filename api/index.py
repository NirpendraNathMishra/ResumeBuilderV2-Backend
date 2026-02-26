"""
Vercel Serverless Entry Point — exposes the FastAPI app as a handler.
"""
from main import app

# Vercel automatically picks up `app` as an ASGI handler
