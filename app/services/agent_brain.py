import json
import logging
from typing import Dict, Any
from app.core.config import settings
from app.core.system_prompt import SYSTEM_PROMPT
from app.services.langchain_tools import ALL_TOOLS
from app.services.platform_client import platform_client

logger = logging.getLogger("uvicorn")

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

        # Rule-based fallback if LLM is unconfigured or encounters an error
        return await self._fallback_rule_processing(prompt, action)

    async def _fallback_rule_processing(self, prompt: str, action: str = None) -> Dict[str, Any]:
        p = prompt.strip().lower()

        if action == "validate" or "validate" in p or "email check" in p or "invalid email" in p:
            contacts = await platform_client.get_all_contacts()
            if not contacts:
                return {
                    "reply": "Attempted to validate contacts, but no records found on Platform.",
                    "action_type": "validate",
                    "data": []
                }
            invalid_list = [c for c in contacts if not c.get("is_valid", True)]
            if invalid_list:
                invalid_names = ", ".join([f"{c['name']} ({c['email']})" for c in invalid_list])
                reply = f"🔍 **Email Validation Completed!** Scanned {len(contacts)} contacts. Found {len(invalid_list)} invalid email format(s):\n• {invalid_names}"
            else:
                reply = f"🔍 **Email Validation Completed!** Scanned {len(contacts)} contacts. All email formats are valid! ✅"
            return {"reply": reply, "action_type": "validate", "data": invalid_list}

        if action == "stats" or "stat" in p or "summary" in p or "how many" in p or "breakdown" in p:
            stats = await platform_client.get_stats()
            if not stats:
                return {"reply": "Could not retrieve stats. Verify platform on Port 8000.", "action_type": "stats", "data": {}}
            reply = f"📊 **Contact Platform Statistics:**\n" \
                    f"• Total Contacts: **{stats.get('total_contacts', 0)}**\n" \
                    f"• Total Companies: **{stats.get('total_companies', 0)}**\n" \
                    f"• Work Contacts: **{stats.get('work_contacts', 0)}**\n" \
                    f"• Personal Contacts: **{stats.get('personal_contacts', 0)}**"
            return {"reply": reply, "action_type": "stats", "data": stats}

        contacts = await platform_client.get_all_contacts(query=prompt)
        if contacts:
            summary_lines = [f"• 👤 **{c['name']}** ({c.get('company', '')}) — 📧 `{c['email']}` | 📞 `{c['phone']}`" for c in contacts]
            reply = f"Found **{len(contacts)}** contact(s):\n\n" + "\n".join(summary_lines)
            return {"reply": reply, "action_type": "search", "data": contacts}

        return {
            "reply": "No matching contacts found. (Note: For enhanced LLM understanding, check your GROQ_API_KEY configuration).",
            "action_type": "search",
            "data": []
        }

agent_brain = AgentBrain()
