import httpx
import logging
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger("uvicorn")

class PlatformClient:
    def __init__(self):
        self.base_url = settings.PLATFORM_API_URL.rstrip('/')

    async def get_all_contacts(self, query: Optional[str] = None, category: Optional[str] = None) -> List[dict]:
        params = {}
        if query:
            params["query"] = query
        if category:
            params["category"] = category

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/contacts", params=params)
                if res.status_code == 200:
                    return res.json()
                logger.error(f"Platform API error: {res.status_code} - {res.text}")
                return []
        except Exception as e:
            logger.error(f"Failed to connect to Platform API at {self.base_url}: {e}")
            return []

    async def get_contact_by_id(self, contact_id: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/contacts/{contact_id}")
                if res.status_code == 200:
                    return res.json()
                return None
        except Exception as e:
            logger.error(f"Failed to fetch contact #{contact_id}: {e}")
            return None

    async def get_stats(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/contacts/stats")
                if res.status_code == 200:
                    return res.json()
                return {}
        except Exception as e:
            logger.error(f"Failed to fetch platform stats: {e}")
            return {}

platform_client = PlatformClient()
