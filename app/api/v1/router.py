from fastapi import APIRouter
from app.api.v1 import bot

api_router = APIRouter()
api_router.include_router(bot.router)
