"""
Resume Builder V2 — FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from resume_controller import router as resume_router

app = FastAPI(
    title="Resume Builder V2",
    description="Multi-field LaTeX resume generator API",
    version="2.0.0",
)

# CORS — allow all origins (configure specific origins in production if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume_router)
