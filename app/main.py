import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Standalone AI Agent Bot service for Contact Book Platform.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount API Router (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

# 2. Mount Static ChatGPT-Style UI (No Jinja2 required)
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "static"))

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
