import httpx
import logging
from typing import List, Optional, Any, Dict
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
        self.init_error = None

        if _HAS_MUDRAID:
            try:
                self.agent = Agent()
                logger.info(f"MudraID Agent initialized successfully (Key ID: {self.agent.api_key_id})")
            except Exception as e:
                self.init_error = self._handle_exception(e, "Agent Initialization")

    def _get_headers(self) -> dict:
        return {}

    def get_active_token(self) -> dict:
        """Retrieve and inspect the current signed MudraID Bearer Access Token."""
        if not self.agent:
            return {
                "status": "error",
                "error": True,
                "error_type": "MudraIDConfigError",
                "message": "Agent not initialized. Check MUDRAID_API_KEY_ID and MUDRAID_SECRET in .env."
            }
        try:
            platform_id = self.agent._platforms.resolve(self.base_url)
            token = self.agent._tokens.get_token(platform_id)
            return {
                "status": "success",
                "platform_id": platform_id,
                "token_type": "Bearer",
                "access_token": token
            }
        except Exception as e:
            return self._handle_exception(e, "Fetch Active Token")

    def _check_agent(self, operation: str) -> Optional[dict]:
        if not self.agent:
            if self.init_error:
                err = dict(self.init_error)
                err["operation"] = operation
                return err
            return {
                "status": "error",
                "error": True,
                "error_type": "MudraIDConfigError",
                "operation": operation,
                "what_it_means": "MudraID credentials missing or blank. Agent could not initialize.",
                "how_to_fix": "Check MUDRAID_API_KEY_ID and MUDRAID_SECRET are set in .env or system environment."
            }
        return None

    def _handle_exception(self, e: Exception, operation: str) -> dict:
        error_type = type(e).__name__
        what_it_means = str(e)
        how_to_fix = "Check logs and configuration."

        if _HAS_MUDRAID and isinstance(e, MudraIDError):
            if isinstance(e, MudraIDConfigError):
                error_type = "MudraIDConfigError"
                what_it_means = "Credentials missing or blank."
                how_to_fix = "Check MUDRAID_API_KEY_ID and MUDRAID_SECRET are set in .env or system environment."
            elif isinstance(e, MudraIDAuthError):
                error_type = "MudraIDAuthError"
                what_it_means = "MudraID rejected the credentials."
                how_to_fix = "The key id / secret pair is wrong — rotate or re-check in MudraID portal."
            elif isinstance(e, MudraIDRevokedError):
                error_type = "MudraIDRevokedError"
                what_it_means = "The agent is inactive, or lacks platform/scope access."
                how_to_fix = "Check the agent's status and grants in the MudraID portal."
            elif isinstance(e, MudraIDPlatformNotRegisteredError):
                error_type = "MudraIDPlatformNotRegisteredError"
                what_it_means = "The host you called isn't a platform this agent is registered with."
                how_to_fix = "Register the agent for that platform, or check PLATFORM_API_URL in .env."
            elif isinstance(e, MudraIDScopeError):
                error_type = "MudraIDScopeError"
                what_it_means = "Insufficient permissions/scopes granted to this agent."
                how_to_fix = "Request/grant required scopes for the agent in MudraID portal."
            elif isinstance(e, MudraIDNetworkError):
                error_type = "MudraIDNetworkError"
                what_it_means = "Could not connect to MudraID servers."
                how_to_fix = "Check network connection or verify MUDRAID_BASE_URL setting."

            logger.error(
                f"\n==================== MudraID Agent Error ====================\n"
                f" Error Type   : {error_type}\n"
                f" Operation    : {operation}\n"
                f" What it means: {what_it_means}\n"
                f" How to fix   : {how_to_fix}\n"
                f"=================================================================\n"
            )
        else:
            logger.error(f"❌ Failed to execute {operation} at {self.base_url}: {e}")

        return {
            "status": "error",
            "error": True,
            "error_type": error_type,
            "operation": operation,
            "what_it_means": what_it_means,
            "how_to_fix": how_to_fix
        }

    def _handle_response_error(self, res, operation: str) -> dict:
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

        return {
            "status": "error",
            "error": True,
            "error_type": error_code,
            "status_code": status_code,
            "operation": operation,
            "what_it_means": what_it_means,
            "how_to_fix": fix
        }

    # Personal Contact Operations
    async def get_all_contacts(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        query: Optional[str] = None
    ) -> Any:
        err = self._check_agent("Get All Contacts")
        if err:
            return err

        params = {}
        if name: params["name"] = name
        if email: params["email"] = email
        if query: params["query"] = query

        try:
            res = self.agent.get(f"{self.base_url}/contacts", params=params)
            if res.status_code == 200:
                return res.json()
            return self._handle_response_error(res, "Get All Contacts")
        except Exception as e:
            return self._handle_exception(e, "Get All Contacts")

    async def create_contact(
        self,
        name: str,
        email: str,
        phone: str,
        notes: Optional[str] = None
    ) -> Any:
        err = self._check_agent("Create Contact")
        if err:
            return err

        payload = {"name": name, "email": email, "phone": phone}
        if notes: payload["notes"] = notes

        try:
            res = self.agent.post(f"{self.base_url}/contacts", json=payload)
            if res.status_code in (200, 201):
                return res.json()
            return self._handle_response_error(res, "Create Contact")
        except Exception as e:
            return self._handle_exception(e, "Create Contact")

    async def update_contact(
        self,
        contact_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Any:
        err = self._check_agent("Update Contact")
        if err:
            return err

        payload = {}
        if name: payload["name"] = name
        if email: payload["email"] = email
        if phone: payload["phone"] = phone
        if notes: payload["notes"] = notes

        try:
            res = self.agent.put(f"{self.base_url}/contacts/{contact_id}", json=payload)
            if res.status_code == 200:
                return res.json()
            return self._handle_response_error(res, "Update Contact")
        except Exception as e:
            return self._handle_exception(e, "Update Contact")

    async def delete_contact(self, contact_id: str) -> Any:
        err = self._check_agent("Delete Contact")
        if err:
            return err

        try:
            res = self.agent.delete(f"{self.base_url}/contacts/{contact_id}")
            if res.status_code == 200:
                return {"status": "success", "message": f"Contact {contact_id} deleted."}
            return self._handle_response_error(res, "Delete Contact")
        except Exception as e:
            return self._handle_exception(e, "Delete Contact")

    # Company Contact Operations
    async def get_all_companies(
        self,
        name: Optional[str] = None,
        company_email: Optional[str] = None,
        location: Optional[str] = None,
        query: Optional[str] = None
    ) -> Any:
        err = self._check_agent("Get All Companies")
        if err:
            return err

        params = {}
        if name: params["name"] = name
        if company_email: params["company_email"] = company_email
        if location: params["location"] = location
        if query: params["query"] = query

        try:
            res = self.agent.get(f"{self.base_url}/companies", params=params)
            if res.status_code == 200:
                return res.json()
            return self._handle_response_error(res, "Get All Companies")
        except Exception as e:
            return self._handle_exception(e, "Get All Companies")

    async def create_company(
        self,
        name: str,
        company_email: str,
        phone: str,
        location: str,
        notes: Optional[str] = None
    ) -> Any:
        err = self._check_agent("Create Company")
        if err:
            return err

        payload = {
            "name": name,
            "company_email": company_email,
            "phone": phone,
            "location": location
        }
        if notes: payload["notes"] = notes

        try:
            res = self.agent.post(f"{self.base_url}/companies", json=payload)
            if res.status_code in (200, 201):
                return res.json()
            return self._handle_response_error(res, "Create Company")
        except Exception as e:
            return self._handle_exception(e, "Create Company")

    async def update_company(
        self,
        company_id: str,
        name: Optional[str] = None,
        company_email: Optional[str] = None,
        phone: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Any:
        err = self._check_agent("Update Company")
        if err:
            return err

        payload = {}
        if name: payload["name"] = name
        if company_email: payload["company_email"] = company_email
        if phone: payload["phone"] = phone
        if location: payload["location"] = location
        if notes: payload["notes"] = notes

        try:
            res = self.agent.put(f"{self.base_url}/companies/{company_id}", json=payload)
            if res.status_code == 200:
                return res.json()
            return self._handle_response_error(res, "Update Company")
        except Exception as e:
            return self._handle_exception(e, "Update Company")

    async def delete_company(self, company_id: str) -> Any:
        err = self._check_agent("Delete Company")
        if err:
            return err

        try:
            res = self.agent.delete(f"{self.base_url}/companies/{company_id}")
            if res.status_code == 200:
                return {"status": "success", "message": f"Company contact {company_id} deleted."}
            return self._handle_response_error(res, "Delete Company")
        except Exception as e:
            return self._handle_exception(e, "Delete Company")

    async def get_stats(self) -> Any:
        err = self._check_agent("Get Stats")
        if err:
            return err

        try:
            c_res = self.agent.get(f"{self.base_url}/contacts/stats")
            if c_res.status_code != 200:
                return self._handle_response_error(c_res, "Get Stats (Contacts)")
            comp_res = self.agent.get(f"{self.base_url}/companies/stats")
            if comp_res.status_code != 200:
                return self._handle_response_error(comp_res, "Get Stats (Companies)")

            total_contacts = c_res.json().get("total_contacts", 0)
            total_companies = comp_res.json().get("total_companies", 0)
            return {"total_contacts": total_contacts, "total_companies": total_companies}
        except Exception as e:
            return self._handle_exception(e, "Get Stats")

platform_client = PlatformClient()
