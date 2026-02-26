"""
Vercel Serverless Entry Point — exposes the FastAPI app as a handler.
"""
import sys
import os

# Add the project root to sys.path so we can import main, config, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
