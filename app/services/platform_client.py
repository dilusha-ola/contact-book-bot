import httpx
import logging
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger("uvicorn")

class PlatformClient:
    def __init__(self):
        self.base_url = settings.PLATFORM_API_URL.rstrip('/')

    async def get_all_contacts(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        category: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[dict]:
        params = {}
        if name:
            params["name"] = name
        if email:
            params["email"] = email
        if company:
            params["company"] = company
        if category:
            params["category"] = category
        if query:
            params["query"] = query

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

    async def create_contact(
        self,
        name: str,
        email: str,
        phone: str,
        company: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[dict]:
        payload = {
            "name": name,
            "email": email,
            "phone": phone
        }
        if company:
            payload["company"] = company
        if category:
            payload["category"] = category
        if notes:
            payload["notes"] = notes

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{self.base_url}/contacts", json=payload)
                if res.status_code in (200, 201):
                    return res.json()
                logger.error(f"Failed to create contact: {res.status_code} - {res.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return None

    async def update_contact(
        self,
        contact_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[dict]:
        payload = {}
        if name is not None:
            payload["name"] = name
        if email is not None:
            payload["email"] = email
        if phone is not None:
            payload["phone"] = phone
        if company is not None:
            payload["company"] = company
        if category is not None:
            payload["category"] = category
        if notes is not None:
            payload["notes"] = notes

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.put(f"{self.base_url}/contacts/{contact_id}", json=payload)
                if res.status_code == 200:
                    return res.json()
                logger.error(f"Failed to update contact #{contact_id}: {res.status_code} - {res.text}")
                return None
        except Exception as e:
            logger.error(f"Error updating contact #{contact_id}: {e}")
            return None

    async def delete_contact(self, contact_id: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.delete(f"{self.base_url}/contacts/{contact_id}")
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Error deleting contact #{contact_id}: {e}")
            return False

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

