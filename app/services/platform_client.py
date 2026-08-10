import httpx
import logging
from typing import List, Optional
from app.core.config import settings

try:
    # pyrefly: ignore [missing-import]
    from mudraid import (
        Agent,
        MudraIDConfigError,
        MudraIDAuthError,
        MudraIDRevokedError,
        MudraIDPlatformNotRegisteredError,
        MudraIDScopeError,
        MudraIDNetworkError,
        MudraIDError,
    )
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
                self._handle_exception(e, "Agent Initialization")

    def _get_headers(self) -> dict:
        # No fixed X-API-Key header sent from the bot side.
        # MudraID Agent SDK manages authorization via Bearer tokens automatically.
        return {}

    def _handle_exception(self, e: Exception, operation: str):
        if _HAS_MUDRAID and isinstance(e, MudraIDError):
            if isinstance(e, MudraIDConfigError):
                logger.error(
                    f"\n==================== MudraID Agent Error ====================\n"
                    f" Error Type   : MudraIDConfigError\n"
                    f" Operation    : {operation}\n"
                    f" What it means: Credentials missing or blank.\n"
                    f" How to fix   : Check MUDRAID_API_KEY_ID and MUDRAID_SECRET are set in .env or system environment.\n"
                    f"=================================================================\n"
                )
            elif isinstance(e, MudraIDAuthError):
                logger.error(
                    f"\n==================== MudraID Agent Error ====================\n"
                    f" Error Type   : MudraIDAuthError\n"
                    f" Operation    : {operation}\n"
                    f" What it means: MudraID rejected the credentials.\n"
                    f" How to fix   : The key id / secret pair is wrong — rotate or re-check in MudraID portal.\n"
                    f"=================================================================\n"
                )
            elif isinstance(e, MudraIDRevokedError):
                logger.error(
                    f"\n==================== MudraID Agent Error ====================\n"
                    f" Error Type   : MudraIDRevokedError\n"
                    f" Operation    : {operation}\n"
                    f" What it means: The agent is inactive, or lacks platform/scope access.\n"
                    f" How to fix   : Check the agent's status and grants in the MudraID portal.\n"
                    f"=================================================================\n"
                )
            elif isinstance(e, MudraIDPlatformNotRegisteredError):
                logger.error(
                    f"\n==================== MudraID Agent Error ====================\n"
                    f" Error Type   : MudraIDPlatformNotRegisteredError\n"
                    f" Operation    : {operation}\n"
                    f" What it means: The host you called isn't a platform this agent is registered with.\n"
                    f" How to fix   : Register the agent for that platform, or check PLATFORM_API_URL in .env.\n"
                    f"=================================================================\n"
                )
            elif isinstance(e, MudraIDScopeError):
                logger.error(
                    f"\n==================== MudraID Agent Error ====================\n"
                    f" Error Type   : MudraIDScopeError\n"
                    f" Operation    : {operation}\n"
                    f" What it means: Insufficient permissions/scopes granted to this agent.\n"
                    f" How to fix   : Request/grant required scopes for the agent in MudraID portal.\n"
                    f"=================================================================\n"
                )
            elif isinstance(e, MudraIDNetworkError):
                logger.error(
                    f"\n==================== MudraID Agent Error ====================\n"
                    f" Error Type   : MudraIDNetworkError\n"
                    f" Operation    : {operation}\n"
                    f" What it means: Could not connect to MudraID servers.\n"
                    f" How to fix   : Check network connection or verify MUDRAID_BASE_URL setting.\n"
                    f"=================================================================\n"
                )
            else:
                logger.error(f"❌ MudraID Error during {operation}: {e}")
        else:
            logger.error(f"❌ Failed to execute {operation} at {self.base_url}: {e}")

    def _handle_response_error(self, res, operation: str):
        status_code = res.status_code
        error_code = "UNKNOWN"
        what_it_means = f"Platform API returned error {status_code}"
        fix = "Inspect platform server logs for details."

        try:
            data = res.json()
            error_code = data.get("error_code", "UNKNOWN")
            if "what_it_means" in data:
                what_it_means = data["what_it_means"]
            if "fix" in data:
                fix = data["fix"]
        except Exception:
            pass

        if error_code == "WRONG_AUDIENCE" or status_code == 403:
            what_it_means = "Your YAML's platform_id doesn't match what MudraID issued."
            fix = "Re-export mudraid_scopes.yaml from the portal and redeploy."
        elif error_code == "MIDDLEWARE_NOT_READY" or status_code == 500:
            what_it_means = "The YAML couldn't be loaded or parsed on the platform server."
            fix = "Fix the scopes.yaml file; the next request recovers without a restart."
        elif error_code == "JWKS_UNAVAILABLE":
            what_it_means = "The platform middleware couldn't reach MudraID's keys."
            fix = "Transient network issue to MudraID; check connectivity on platform server."
        elif status_code == 404:
            what_it_means = "A route unexpectedly 404s (it has no rule in the YAML, or is marked skip)."
            fix = "Add a rule for this route in mudraid_scopes.yaml on the platform server."

        logger.error(
            f"\n==================== MudraID Platform Response Error ====================\n"
            f" Operation    : {operation}\n"
            f" Status Code  : {status_code}\n"
            f" Error Code   : {error_code}\n"
            f" What it means: {what_it_means}\n"
            f" How to fix   : {fix}\n"
            f"=========================================================================\n"
        )

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
                self._handle_response_error(res, "Get All Contacts")
                return []
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.get(f"{self.base_url}/contacts", params=params)
                    if res.status_code == 200:
                        return res.json()
                    self._handle_response_error(res, "Get All Contacts")
                    return []
        except Exception as e:
            self._handle_exception(e, "Get All Contacts")
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
                self._handle_response_error(res, "Create Contact")
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.post(f"{self.base_url}/contacts", json=payload)
                    if res.status_code in (200, 201):
                        return res.json()
                    self._handle_response_error(res, "Create Contact")
                    return None
        except Exception as e:
            self._handle_exception(e, "Create Contact")
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
                self._handle_response_error(res, "Update Contact")
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.put(f"{self.base_url}/contacts/{contact_id}", json=payload)
                    if res.status_code == 200:
                        return res.json()
                    self._handle_response_error(res, "Update Contact")
                    return None
        except Exception as e:
            self._handle_exception(e, "Update Contact")
            return None

    async def delete_contact(self, contact_id: str) -> bool:
        try:
            if self.agent:
                res = self.agent.delete(f"{self.base_url}/contacts/{contact_id}")
                if res.status_code == 200:
                    return True
                self._handle_response_error(res, "Delete Contact")
                return False
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.delete(f"{self.base_url}/contacts/{contact_id}")
                    if res.status_code == 200:
                        return True
                    self._handle_response_error(res, "Delete Contact")
                    return False
        except Exception as e:
            self._handle_exception(e, "Delete Contact")
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
                self._handle_response_error(res, "Get All Companies")
                return []
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.get(f"{self.base_url}/companies", params=params)
                    if res.status_code == 200:
                        return res.json()
                    self._handle_response_error(res, "Get All Companies")
                    return []
        except Exception as e:
            self._handle_exception(e, "Get All Companies")
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
                self._handle_response_error(res, "Create Company")
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.post(f"{self.base_url}/companies", json=payload)
                    if res.status_code in (200, 201):
                        return res.json()
                    self._handle_response_error(res, "Create Company")
                    return None
        except Exception as e:
            self._handle_exception(e, "Create Company")
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
                self._handle_response_error(res, "Update Company")
                return None
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.put(f"{self.base_url}/companies/{company_id}", json=payload)
                    if res.status_code == 200:
                        return res.json()
                    self._handle_response_error(res, "Update Company")
                    return None
        except Exception as e:
            self._handle_exception(e, "Update Company")
            return None

    async def delete_company(self, company_id: str) -> bool:
        try:
            if self.agent:
                res = self.agent.delete(f"{self.base_url}/companies/{company_id}")
                if res.status_code == 200:
                    return True
                self._handle_response_error(res, "Delete Company")
                return False
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    res = await client.delete(f"{self.base_url}/companies/{company_id}")
                    if res.status_code == 200:
                        return True
                    self._handle_response_error(res, "Delete Company")
                    return False
        except Exception as e:
            self._handle_exception(e, "Delete Company")
            return False

    async def get_stats(self) -> dict:
        try:
            if self.agent:
                c_res = self.agent.get(f"{self.base_url}/contacts/stats")
                comp_res = self.agent.get(f"{self.base_url}/companies/stats")
                total_contacts = c_res.json().get("total_contacts", 0) if c_res.status_code == 200 else 0
                total_companies = comp_res.json().get("total_companies", 0) if comp_res.status_code == 200 else 0
                if c_res.status_code != 200:
                    self._handle_response_error(c_res, "Get Stats (Contacts)")
                if comp_res.status_code != 200:
                    self._handle_response_error(comp_res, "Get Stats (Companies)")
                return {"total_contacts": total_contacts, "total_companies": total_companies}
            else:
                async with httpx.AsyncClient(timeout=15.0, headers=self._get_headers()) as client:
                    c_res = await client.get(f"{self.base_url}/contacts/stats")
                    comp_res = await client.get(f"{self.base_url}/companies/stats")
                    total_contacts = c_res.json().get("total_contacts", 0) if c_res.status_code == 200 else 0
                    total_companies = comp_res.json().get("total_companies", 0) if comp_res.status_code == 200 else 0
                    return {"total_contacts": total_contacts, "total_companies": total_companies}
        except Exception as e:
            self._handle_exception(e, "Get Stats")
            return {"total_contacts": 0, "total_companies": 0}

platform_client = PlatformClient()
