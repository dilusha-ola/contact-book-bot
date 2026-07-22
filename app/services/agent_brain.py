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
        self.agent_executor = None
        self._init_llm_agent()

    def _init_llm_agent(self):
        try:
            api_key = settings.GROQ_API_KEY or settings.OPENAI_API_KEY or settings.GOOGLE_API_KEY
            if not api_key:
                logger.warning("No LLM API key provided. Agent running in fallback rule-based mode.")
                return

            if settings.LLM_PROVIDER.lower() == "groq" or (settings.GROQ_API_KEY and not settings.OPENAI_API_KEY):
                from langchain_groq import ChatGroq
                llm = ChatGroq(
                    groq_api_key=settings.GROQ_API_KEY,
                    model_name=settings.LLM_MODEL or "llama-3.3-70b-versatile",
                    temperature=0.1
                )
            elif settings.LLM_PROVIDER.lower() == "google" or settings.GOOGLE_API_KEY:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    google_api_key=settings.GOOGLE_API_KEY,
                    model=settings.LLM_MODEL or "gemini-1.5-flash",
                    temperature=0.1
                )
            else:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    model=settings.LLM_MODEL or "gpt-4o-mini",
                    temperature=0.1
                )

            from langchain.agents import create_tool_calling_agent, AgentExecutor
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])

            agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
            self.agent_executor = AgentExecutor(agent=agent, tools=ALL_TOOLS, verbose=True)
            logger.info(f"LangChain LLM Agent successfully initialized with {settings.LLM_PROVIDER} / {settings.LLM_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain LLM Agent: {e}")
            self.agent_executor = None

    async def process_prompt(self, prompt: str, action: str = None) -> Dict[str, Any]:
        if not self.agent_executor:
            self._init_llm_agent()

        if self.agent_executor:
            try:
                res = await self.agent_executor.ainvoke({"input": prompt})
                output_text = res.get("output", "")
                return {
                    "reply": output_text,
                    "action_type": "llm_agent",
                    "data": res.get("intermediate_steps", None)
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
