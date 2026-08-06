import httpx
import logging
from typing import List, Optional
from app.core.config import settings

try:
    # pyrefly: ignore [missing-import]
    from mudraid import Agent
    _HAS_MUDRAID = True
except ImportError:
    _HAS_MUDRAID = False

logger = logging.getLogger("uvicorn")

class PlatformClient:
    def __init__(self):
        self.base_url = settings.PLATFORM_API_URL.rstrip('/')
        self.agent = None

        if _HAS_MUDRAID:
            try:
                self.agent = Agent()
                logger.info(f"MudraID Agent initialized successfully (Key ID: {self.agent.api_key_id})")
            except Exception as e:
                logger.warning(f"Could not initialize MudraID Agent ({e}). Falling back to standard HTTP calls.")

    def _get_headers(self) -> dict:
        headers = {}
        if settings.PLATFORM_API_KEY:
            headers["X-API-Key"] = settings.PLATFORM_API_KEY
        return headers

    # Personal Contact Operations
    async def get_all_contacts(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[dict]:
        params = {}
        if name: params["name"] = name
        if email: params["email"] = email
        if query: params["query"] = query

        try:
            if self.agent:
                res = self.agent.get(f"{self.base_url}/contacts", params=params)
                if res.status_code == 200:
                    return res.json()
                logger.error(f"Platform API error (MudraID Agent): {res.status_code} - {res.text}")
                return []
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.get(f"{self.base_url}/contacts", params=params)
                    if res.status_code == 200:
                        return res.json()
                    logger.error(f"Platform API error: {res.status_code} - {res.text}")
                    return []
        except Exception as e:
            logger.error(f"Failed to connect to Platform API at {self.base_url}: {e}")
            return []

    async def create_contact(
        self,
        name: str,
        email: str,
        phone: str,
        notes: Optional[str] = None
    ) -> Optional[dict]:
        payload = {"name": name, "email": email, "phone": phone}
        if notes: payload["notes"] = notes

        try:
            if self.agent:
                res = self.agent.post(f"{self.base_url}/contacts", json=payload)
                if res.status_code in (200, 201):
                    return res.json()
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.post(f"{self.base_url}/contacts", json=payload)
                    if res.status_code in (200, 201):
                        return res.json()
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
        notes: Optional[str] = None
    ) -> Optional[dict]:
        payload = {}
        if name: payload["name"] = name
        if email: payload["email"] = email
        if phone: payload["phone"] = phone
        if notes: payload["notes"] = notes

        try:
            if self.agent:
                res = self.agent.put(f"{self.base_url}/contacts/{contact_id}", json=payload)
                if res.status_code == 200:
                    return res.json()
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.put(f"{self.base_url}/contacts/{contact_id}", json=payload)
                    if res.status_code == 200:
                        return res.json()
                    return None
        except Exception as e:
            logger.error(f"Error updating contact #{contact_id}: {e}")
            return None

    async def delete_contact(self, contact_id: str) -> bool:
        try:
            if self.agent:
                res = self.agent.delete(f"{self.base_url}/contacts/{contact_id}")
                return res.status_code == 200
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.delete(f"{self.base_url}/contacts/{contact_id}")
                    return res.status_code == 200
        except Exception as e:
            logger.error(f"Error deleting contact #{contact_id}: {e}")
            return False

    # Company Contact Operations
    async def get_all_companies(
        self,
        name: Optional[str] = None,
        company_email: Optional[str] = None,
        location: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[dict]:
        params = {}
        if name: params["name"] = name
        if company_email: params["company_email"] = company_email
        if location: params["location"] = location
        if query: params["query"] = query

        try:
            if self.agent:
                res = self.agent.get(f"{self.base_url}/companies", params=params)
                if res.status_code == 200:
                    return res.json()
                return []
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.get(f"{self.base_url}/companies", params=params)
                    if res.status_code == 200:
                        return res.json()
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch companies: {e}")
            return []

    async def create_company(
        self,
        name: str,
        company_email: str,
        phone: str,
        location: str,
        notes: Optional[str] = None
    ) -> Optional[dict]:
        payload = {
            "name": name,
            "company_email": company_email,
            "phone": phone,
            "location": location
        }
        if notes: payload["notes"] = notes

        try:
            if self.agent:
                res = self.agent.post(f"{self.base_url}/companies", json=payload)
                if res.status_code in (200, 201):
                    return res.json()
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.post(f"{self.base_url}/companies", json=payload)
                    if res.status_code in (200, 201):
                        return res.json()
                    return None
        except Exception as e:
            logger.error(f"Error creating company: {e}")
            return None

    async def update_company(
        self,
        company_id: str,
        name: Optional[str] = None,
        company_email: Optional[str] = None,
        phone: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[dict]:
        payload = {}
        if name: payload["name"] = name
        if company_email: payload["company_email"] = company_email
        if phone: payload["phone"] = phone
        if location: payload["location"] = location
        if notes: payload["notes"] = notes

        try:
            if self.agent:
                res = self.agent.put(f"{self.base_url}/companies/{company_id}", json=payload)
                if res.status_code == 200:
                    return res.json()
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.put(f"{self.base_url}/companies/{company_id}", json=payload)
                    if res.status_code == 200:
                        return res.json()
                    return None
        except Exception as e:
            logger.error(f"Error updating company #{company_id}: {e}")
            return None

    async def delete_company(self, company_id: str) -> bool:
        try:
            if self.agent:
                res = self.agent.delete(f"{self.base_url}/companies/{company_id}")
                return res.status_code == 200
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.delete(f"{self.base_url}/companies/{company_id}")
                    return res.status_code == 200
        except Exception as e:
            logger.error(f"Error deleting company #{company_id}: {e}")
            return False

    async def get_stats(self) -> dict:
        try:
            if self.agent:
                c_res = self.agent.get(f"{self.base_url}/contacts/stats")
                comp_res = self.agent.get(f"{self.base_url}/companies/stats")
                total_contacts = c_res.json().get("total_contacts", 0) if c_res.status_code == 200 else 0
                total_companies = comp_res.json().get("total_companies", 0) if comp_res.status_code == 200 else 0
                return {"total_contacts": total_contacts, "total_companies": total_companies}
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    c_res = await client.get(f"{self.base_url}/contacts/stats")
                    comp_res = await client.get(f"{self.base_url}/companies/stats")
                    total_contacts = c_res.json().get("total_contacts", 0) if c_res.status_code == 200 else 0
                    total_companies = comp_res.json().get("total_companies", 0) if comp_res.status_code == 200 else 0
                    return {"total_contacts": total_contacts, "total_companies": total_companies}
        except Exception as e:
            logger.error(f"Failed to fetch stats: {e}")
            return {"total_contacts": 0, "total_companies": 0}

platform_client = PlatformClient()
