import json
import logging
import re
from typing import Dict, Any
from app.core.config import settings
from app.core.system_prompt import SYSTEM_PROMPT
from app.services.langchain_tools import ALL_TOOLS
from app.services.platform_client import platform_client

logger = logging.getLogger("uvicorn")

def extract_fields(prompt: str) -> Dict[str, str]:
    fields = {}
    # 1. Extract explicit assignments (e.g. name = John Doe, email = john@gmail.com, location: Colombo)
    for match in re.finditer(r"(name|email|company_email|phone|location|notes)\s*[:=]\s*([^,\n;]+)", prompt, re.I):
        k = match.group(1).lower()
        v = match.group(2).strip()
        fields[k] = v

    # 2. Extract email if not set via assignment
    if "email" not in fields and "company_email" not in fields:
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", prompt)
        if email_match:
            fields["email"] = email_match.group(0)

    # 3. Extract phone if not set via assignment
    if "phone" not in fields:
        phone_match = re.search(r"(\+?\d{9,13})", prompt)
        if phone_match:
            fields["phone"] = phone_match.group(0)

    return fields

class AgentBrain:
    def __init__(self):
        self.agent = None
        self._init_llm_agent()

    def _init_llm_agent(self):
        try:
                    # pyrefly: ignore [missing-import]
            api_key = settings.GROQ_API_KEY or settings.OPENAI_API_KEY or settings.GOOGLE_API_KEY
            if not api_key:
                logger.warning("No LLM API key provided. Agent running in fallback rule-based mode.")
                return

            llm = None
            provider = settings.LLM_PROVIDER.lower()

            if provider == "groq" or (settings.GROQ_API_KEY and not settings.OPENAI_API_KEY):
                try:
                    # pyrefly: ignore [missing-import]
                    from langchain_groq import ChatGroq
                    llm = ChatGroq(
                        groq_api_key=settings.GROQ_API_KEY,
                        model_name=settings.LLM_MODEL or "llama-3.3-70b-versatile",
                        temperature=0.1
                    )
                except ImportError as ie:
                    logger.error(f"langchain_groq import failed: {ie}")

            elif provider == "google" or settings.GOOGLE_API_KEY:
                try:
                    # pyrefly: ignore [missing-import]
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    llm = ChatGoogleGenerativeAI(
                        google_api_key=settings.GOOGLE_API_KEY,
                        model=settings.LLM_MODEL or "gemini-1.5-flash",
                        temperature=0.1
                    )
                except ImportError as ie:
                    logger.error(f"langchain_google_genai import failed: {ie}")

            if not llm and settings.OPENAI_API_KEY:
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        api_key=settings.OPENAI_API_KEY,
                        model=settings.LLM_MODEL or "gpt-4o-mini",
                        temperature=0.1
                    )
                except ImportError as ie:
                    logger.error(f"langchain_openai import failed: {ie}")

            if not llm:
                logger.warning("LLM model initialization failed. Running in fallback rule-based mode.")
                return

            from langchain.agents import create_agent

            self.agent = create_agent(
                model=llm,
                tools=ALL_TOOLS,
                system_prompt=SYSTEM_PROMPT
            )
            logger.info(f"LangChain LLM Agent successfully initialized with {settings.LLM_PROVIDER} / {settings.LLM_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain LLM Agent: {e}")
            self.agent = None

    async def process_prompt(self, prompt: str, action: str = None) -> Dict[str, Any]:
        if not self.agent:
            self._init_llm_agent()

        if self.agent:
            try:
                res = await self.agent.ainvoke({"messages": [("user", prompt)]})
                messages = res.get("messages", [])
                output_text = messages[-1].content if messages else ""
                return {
                    "reply": output_text,
                    "action_type": "llm_agent",
                    "data": None
                }
            except Exception as e:
                logger.error(f"LangChain LLM execution error: {e}")

        # Fallback rule processing if LLM is unconfigured or encounters runtime issues
        return await self._fallback_rule_processing(prompt, action)

    async def _fallback_rule_processing(self, prompt: str, action: str = None) -> Dict[str, Any]:
        p = prompt.strip().lower()
        fields = extract_fields(prompt)
        is_company = "company" in p

        # 1. CREATE Handling (Supports natural language and assignment format)
        if "create" in p or "add" in p or "insert" in p or "new" in p:
            if is_company:
                name = fields.get("name") or fields.get("location") or "New Company"
                comp_email = fields.get("company_email") or fields.get("email") or "info@company.com"
                phone = fields.get("phone") or "0112345678"
                location = fields.get("location") or "Colombo"
                res = await platform_client.create_company(name=name, company_email=comp_email, phone=phone, location=location)
                if res:
                    return {"reply": f"Company contact 🏢 **{res['name']}** (`{res['company_email']}`) has been created successfully.", "action_type": "create", "data": res}
            else:
                name = fields.get("name") or "New Contact"
                email = fields.get("email") or "contact@example.com"
                phone = fields.get("phone") or "0770000000"
                res = await platform_client.create_contact(name=name, email=email, phone=phone)
                if res:
                    return {"reply": f"Personal contact 👤 **{res['name']}** (`{res['email']}`) has been created successfully.", "action_type": "create", "data": res}

        # 2. UPDATE Handling
        if "update" in p or "edit" in p or "change" in p or "modify" in p:
            query = fields.get("email") or fields.get("name") or prompt
            if is_company:
                companies = await platform_client.get_all_companies(query=query)
                if companies:
                    target_id = companies[0]["id"]
                    update_payload = {}
                    if "name" in fields: update_payload["name"] = fields["name"]
                    if "email" in fields: update_payload["company_email"] = fields["email"]
                    if "company_email" in fields: update_payload["company_email"] = fields["company_email"]
                    if "phone" in fields: update_payload["phone"] = fields["phone"]
                    if "location" in fields: update_payload["location"] = fields["location"]
                    res = await platform_client.update_company(target_id, **update_payload)
                    if res:
                        return {"reply": f"Company contact 🏢 **{res['name']}** (`{res['company_email']}`) has been updated successfully.", "action_type": "update", "data": res}
            else:
                contacts = await platform_client.get_all_contacts(query=query)
                if contacts:
                    target_id = contacts[0]["id"]
                    update_payload = {}
                    if "name" in fields: update_payload["name"] = fields["name"]
                    if "email" in fields: update_payload["email"] = fields["email"]
                    if "phone" in fields: update_payload["phone"] = fields["phone"]
                    res = await platform_client.update_contact(target_id, **update_payload)
                    if res:
                        return {"reply": f"Personal contact 👤 **{res['name']}** (`{res['email']}`) has been updated successfully.", "action_type": "update", "data": res}

        # 3. DELETE Handling (Supports natural language and assignment format)
        if "delete" in p or "remove" in p:
            search_query = fields.get("email") or fields.get("name") or prompt
            if is_company:
                companies = await platform_client.get_all_companies(query=search_query)
                if companies:
                    c = companies[0]
                    del_ok = await platform_client.delete_company(c["id"])
                    if del_ok:
                        return {"reply": f"The company contact 🏢 with name **{c['name']}** and email `{c['company_email']}` has been successfully deleted.", "action_type": "delete", "data": c}
            else:
                contacts = await platform_client.get_all_contacts(query=search_query)
                if not contacts and fields.get("email"):
                    contacts = await platform_client.get_all_contacts(email=fields["email"])
                if contacts:
                    c = contacts[0]
                    del_ok = await platform_client.delete_contact(c["id"])
                    if del_ok:
                        return {"reply": f"The personal contact 👤 with name **{c['name']}** and email `{c['email']}` has been successfully deleted.", "action_type": "delete", "data": c}
            return {"reply": "No matching contact found to delete.", "action_type": "delete", "data": None}

        # 4. STATS & SEARCH Handling
        if action == "stats" or "stat" in p or "summary" in p or "how many" in p or "breakdown" in p:
            stats = await platform_client.get_stats()
            reply = f"📊 **Contact Platform Statistics:**\n" \
                    f"• Total Personal Contacts: **{stats.get('total_contacts', 0)}**\n" \
                    f"• Total Company Contacts: **{stats.get('total_companies', 0)}**"
            return {"reply": reply, "action_type": "stats", "data": stats}

        contacts = await platform_client.get_all_contacts(query=prompt)
        if contacts:
            summary_lines = [f"• 👤 **{c['name']}** — 📧 `{c['email']}` | 📞 `{c['phone']}`" for c in contacts]
            reply = f"Found **{len(contacts)}** contact(s):\n\n" + "\n".join(summary_lines)
            return {"reply": reply, "action_type": "search", "data": contacts}

        return {"reply": "No matching contacts found.", "action_type": "search", "data": []}

agent_brain = AgentBrain()
