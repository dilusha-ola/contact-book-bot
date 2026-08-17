import json
import logging
import re
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.system_prompt import SYSTEM_PROMPT
from app.services.langchain_tools import ALL_TOOLS
from app.services.platform_client import platform_client

logger = logging.getLogger("uvicorn")

def extract_fields(prompt: str) -> Dict[str, str]:
    fields = {}
    
    # 1. Extract explicit key = val or key: val assignments
    for match in re.finditer(r"(name|email|company_email|phone|location|notes)\s*[:=]\s*([^,\n;]+)", prompt, re.I):
        k = match.group(1).lower()
        v = match.group(2).strip()
        # Clean trailing keywords if attached in raw string (e.g., 'new phone')
        v_clean = re.split(r"\b(new\s+phone|phone|email|company_email|location|notes|name)\b", v, flags=re.I)[0].strip()
        fields[k] = v_clean or v

    # 2. Extract target email if present in text
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", prompt)
    if email_match:
        fields["target_email"] = email_match.group(0)
        if "email" not in fields:
            fields["email"] = email_match.group(0)

    # 3. Extract phone / new phone number
    phone_match = re.search(r"(?:new\s+phone\s*(?:number)?|phone)\s*[:=]?\s*(\+?\d{9,13})", prompt, re.I)
    if phone_match:
        fields["new_phone"] = phone_match.group(1).strip()
        fields["phone"] = phone_match.group(1).strip()
    elif "phone" not in fields:
        gen_phone = re.search(r"(\+?\d{9,13})", prompt)
        if gen_phone:
            fields["phone"] = gen_phone.group(0)

    # 4. Extract name assignment (e.g. name = perera)
    name_match = re.search(r"name\s*[:=]\s*([a-zA-Z0-9\s]+)", prompt, re.I)
    if name_match:
        raw_name = name_match.group(1).strip()
        clean_name = re.split(r"\b(new|phone|email|company_email|location|notes)\b", raw_name, flags=re.I)[0].strip()
        if clean_name:
            fields["name"] = clean_name
            fields["target_name"] = clean_name

    return fields

class AgentBrain:
    def __init__(self):
        self.agent = None
        self._init_llm_agent()

    def _init_llm_agent(self):
        try:
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
                        model_name=settings.LLM_MODEL or "openai/gpt-oss-120b",
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

        def check_error(obj: Any) -> Optional[Dict[str, Any]]:
            if isinstance(obj, dict) and obj.get("error"):
                err_type = obj.get("error_type", "Error")
                op = obj.get("operation", "Operation")
                means = obj.get("what_it_means", "An unexpected error occurred.")
                fix = obj.get("how_to_fix", "Check configuration and logs.")
                reply = (
                    f"⚠️ **{err_type} encountered during {op}**\n\n"
                    f"• **What it means:** {means}\n"
                    f"• **How to fix:** {fix}"
                )
                return {"reply": reply, "action_type": "error", "data": obj}
            return None

        # Out-of-Domain Guardrail Check (only for explicit non-contact subjects)
        out_of_domain_keywords = ["cricket", "cancer", "vehicle", "vehicles", "brand", "brands", "weather", "recipe", "movie", "capital of", "football", "basketball"]
        if any(k in p for k in out_of_domain_keywords):
            return {
                "reply": "I am specialized strictly as a Contact Book Assistant. I can only assist with managing personal contacts, company contacts, and contact platform statistics. Please ask a contact-related question!",
                "action_type": "out_of_domain",
                "data": None
            }

        # 1. UPDATE Handling (Highest Priority when 'update', 'edit', 'change', 'modify' is in prompt)
        if "update" in p or "edit" in p or "change" in p or "modify" in p:
            search_query = fields.get("target_email") or fields.get("target_name") or fields.get("email") or fields.get("name") or prompt
            clean_search = re.sub(r"\b(update|the|personal|company|contact|phone|number|for|given|details|new|to|with)\b", "", str(search_query), flags=re.I).replace("=", "").replace(":", "").strip()

            if is_company:
                companies = await platform_client.get_all_companies(query=clean_search or search_query)
                err = check_error(companies)
                if err: return err
                if isinstance(companies, list) and companies:
                    target = companies[0]
                    update_payload = {}
                    if fields.get("name") and fields["name"] != target["name"]: update_payload["name"] = fields["name"]
                    if fields.get("email") and fields["email"] != target["company_email"]: update_payload["company_email"] = fields["email"]
                    if fields.get("phone"): update_payload["phone"] = fields["phone"]
                    if fields.get("location"): update_payload["location"] = fields["location"]

                    res = await platform_client.update_company(target["id"], **update_payload)
                    err = check_error(res)
                    if err: return err
                    if res:
                        return {"reply": f"Company contact 🏢 **{res['name']}** (`{res['company_email']}`) has been updated successfully with new phone `{res['phone']}`.", "action_type": "update", "data": res}
            else:
                contacts = await platform_client.get_all_contacts(query=clean_search or search_query)
                err = check_error(contacts)
                if err: return err
                if not contacts and fields.get("target_email"):
                    contacts = await platform_client.get_all_contacts(email=fields["target_email"])
                    err = check_error(contacts)
                    if err: return err
                if isinstance(contacts, list) and contacts:
                    target = contacts[0]
                    update_payload = {}
                    if fields.get("phone"): update_payload["phone"] = fields["phone"]
                    if fields.get("name") and fields["name"].lower() != target["name"].lower(): update_payload["name"] = fields["name"]
                    if fields.get("email") and fields["email"].lower() != target["email"].lower(): update_payload["email"] = fields["email"]

                    res = await platform_client.update_contact(target["id"], **update_payload)
                    err = check_error(res)
                    if err: return err
                    if res:
                        return {"reply": f"Personal contact 👤 **{res['name']}** (`{res['email']}`) has been updated successfully.", "action_type": "update", "data": res}

                return {"reply": f"No contact entry found for **{clean_search or search_query}** in your Contact Book to update.", "action_type": "update", "data": None}

        # 2. CREATE Handling (ONLY if NOT an update request)
        if ("create" in p or "add" in p or "insert" in p or "new contact" in p or "new company" in p) and not ("update" in p or "edit" in p or "change" in p):
            if is_company:
                name = fields.get("name") or fields.get("location") or "New Company"
                comp_email = fields.get("company_email") or fields.get("email") or "info@company.com"
                phone = fields.get("phone") or "0112345678"
                location = fields.get("location") or "Colombo"
                res = await platform_client.create_company(name=name, company_email=comp_email, phone=phone, location=location)
                err = check_error(res)
                if err: return err
                if res:
                    return {"reply": f"Company contact 🏢 **{res['name']}** (`{res['company_email']}`) has been created successfully.", "action_type": "create", "data": res}
            else:
                name = fields.get("name") or "New Contact"
                email = fields.get("email") or "contact@example.com"
                phone = fields.get("phone") or "0770000000"
                res = await platform_client.create_contact(name=name, email=email, phone=phone)
                err = check_error(res)
                if err: return err
                if res:
                    return {"reply": f"Personal contact 👤 **{res['name']}** (`{res['email']}`) has been created successfully.", "action_type": "create", "data": res}

        # 3. DELETE Handling
        if "delete" in p or "remove" in p:
            search_query = fields.get("target_email") or fields.get("target_name") or fields.get("email") or fields.get("name") or prompt
            if is_company:
                companies = await platform_client.get_all_companies(query=search_query)
                err = check_error(companies)
                if err: return err
                if isinstance(companies, list) and companies:
                    c = companies[0]
                    del_ok = await platform_client.delete_company(c["id"])
                    err = check_error(del_ok)
                    if err: return err
                    if del_ok:
                        return {"reply": f"The company contact 🏢 with name **{c['name']}** and email `{c['company_email']}` has been successfully deleted.", "action_type": "delete", "data": c}
            else:
                contacts = await platform_client.get_all_contacts(query=search_query)
                err = check_error(contacts)
                if err: return err
                if not contacts and fields.get("target_email"):
                    contacts = await platform_client.get_all_contacts(email=fields["target_email"])
                    err = check_error(contacts)
                    if err: return err
                if isinstance(contacts, list) and contacts:
                    c = contacts[0]
                    del_ok = await platform_client.delete_contact(c["id"])
                    err = check_error(del_ok)
                    if err: return err
                    if del_ok:
                        return {"reply": f"The personal contact 👤 with name **{c['name']}** and email `{c['email']}` has been successfully deleted.", "action_type": "delete", "data": c}
            return {"reply": "No matching contact found to delete.", "action_type": "delete", "data": None}

        # 4. STATS & UNIFIED SEARCH Handling
        if action == "stats" or "stat" in p or "summary" in p or "how many" in p or "breakdown" in p:
            stats = await platform_client.get_stats()
            err = check_error(stats)
            if err: return err
            reply = f"📊 **Contact Platform Statistics:**\n" \
                    f"• Total Personal Contacts: **{stats.get('total_contacts', 0)}**\n" \
                    f"• Total Company Contacts: **{stats.get('total_companies', 0)}**"
            return {"reply": reply, "action_type": "stats", "data": stats}

        clean_query = prompt.replace("give me contact details of", "").replace("what is", "").replace("who is", "").replace("details of", "").replace("company", "").strip()
        search_term = clean_query or prompt

        companies = await platform_client.get_all_companies(query=search_term)
        err = check_error(companies)
        if err: return err

        contacts = await platform_client.get_all_contacts(query=search_term)
        err = check_error(contacts)
        if err: return err

        if companies or contacts:
            lines = []
            if isinstance(contacts, list) and contacts:
                lines.append("👤 **Personal Contacts:**")
                lines.extend([f"• **{c['name']}** — 📧 `{c['email']}` | 📞 `{c['phone']}`" for c in contacts])
            if isinstance(companies, list) and companies:
                if lines: lines.append("")
                lines.append("🏢 **Company Contacts:**")
                lines.extend([f"• **{c['name']}** ({c['location']}) — 📧 `{c['company_email']}` | 📞 `{c['phone']}`" for c in companies])
            return {"reply": "\n".join(lines), "action_type": "search", "data": {"contacts": contacts, "companies": companies}}

        return {"reply": f"No contact entry found for **{search_term}** in your Contact Book. Would you like me to add them as a new contact?", "action_type": "search", "data": []}

agent_brain = AgentBrain()
