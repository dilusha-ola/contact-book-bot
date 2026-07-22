import re
from typing import Dict, Any
from app.services.platform_client import platform_client

class AgentBrain:
    async def process_prompt(self, prompt: str, action: str = None) -> Dict[str, Any]:
        p = prompt.strip().lower()

        # Action shortcut or keyword: Validate Emails
        if action == "validate" or "validate" in p or "email check" in p or "invalid email" in p:
            contacts = await platform_client.get_all_contacts()
            if not contacts:
                return {
                    "reply": "I attempted to validate contacts, but no records were found on the Platform or the Platform server is offline.",
                    "action_type": "validate",
                    "data": []
                }
            invalid_list = [c for c in contacts if not c.get("is_valid", True)]
            if invalid_list:
                invalid_names = ", ".join([f"{c['name']} ({c['email']})" for c in invalid_list])
                reply = f"🔍 **Email Validation Completed!** Scanned {len(contacts)} contacts. Found {len(invalid_list)} invalid email format(s):\n• {invalid_names}"
            else:
                reply = f"🔍 **Email Validation Completed!** Scanned {len(contacts)} contacts. All email formats are 100% valid! ✅"
            return {
                "reply": reply,
                "action_type": "validate",
                "data": invalid_list
            }

        # Action shortcut or keyword: Category / Stats
        if action == "stats" or "stat" in p or "summary" in p or "how many" in p or "breakdown" in p:
            stats = await platform_client.get_stats()
            if not stats:
                return {
                    "reply": "Could not retrieve stats. Please verify that the Contact Book Platform server is running on Port 8000.",
                    "action_type": "stats",
                    "data": {}
                }
            reply = f"📊 **Contact Platform Statistics:**\n" \
                    f"• Total Contacts: **{stats.get('total_contacts', 0)}**\n" \
                    f"• Total Companies: **{stats.get('total_companies', 0)}**\n" \
                    f"• Work Contacts: **{stats.get('work_contacts', 0)}**\n" \
                    f"• Personal Contacts: **{stats.get('personal_contacts', 0)}**"
            return {
                "reply": reply,
                "action_type": "stats",
                "data": stats
            }

        # Search or Query Intent
        # Extract search keywords (e.g., "find contacts at decryptogen", "search Nimal", "who is tharushi")
        search_target = None
        if "at " in p:
            search_target = p.split("at ")[-1].strip()
        elif "for " in p:
            search_target = p.split("for ")[-1].strip()
        elif "search " in p:
            search_target = p.replace("search", "").strip()
        elif "find " in p:
            search_target = p.replace("find", "").strip()
        elif "who is " in p:
            search_target = p.replace("who is", "").strip()

        # Execute Search query to Platform
        contacts = await platform_client.get_all_contacts(query=search_target)

        if contacts:
            summary_lines = []
            for c in contacts:
                comp = f" at **{c['company']}**" if c.get("company") else ""
                summary_lines.append(f"• 👤 **{c['name']}**{comp} — 📧 `{c['email']}` | 📞 `{c['phone']}` ({c['category']})")
            
            contacts_formatted = "\n".join(summary_lines)
            reply = f"Found **{len(contacts)}** contact(s) matching your request:\n\n{contacts_formatted}"
            return {
                "reply": reply,
                "action_type": "search",
                "data": contacts
            }
        else:
            if search_target:
                reply = f"I searched the Platform API for **'{search_target}'**, but no matching contacts were found."
            else:
                reply = "I connected to the Contact Book Platform API, but no contacts are currently stored in MongoDB Atlas."
            return {
                "reply": reply,
                "action_type": "search",
                "data": []
            }

agent_brain = AgentBrain()
