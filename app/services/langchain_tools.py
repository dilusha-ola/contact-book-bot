import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from app.services.platform_client import platform_client

@tool
async def list_contacts_tool(
    name: Optional[str] = None,
    email: Optional[str] = None,
    company: Optional[str] = None,
    category: Optional[str] = None,
    query: Optional[str] = None
) -> str:
    """
    Search and filter contacts from the Contact Book Platform.
    
    Args:
        name: Filter specifically by contact name (e.g. 'Nimal').
        email: Filter specifically by email address (e.g. 'nimal@gmail.com').
        company: Filter specifically by company (e.g. 'Decryptogen').
        category: Filter by contact category ('Work' or 'Personal').
        query: General search term across name, email, or company.
    """
    contacts = await platform_client.get_all_contacts(
        name=name,
        email=email,
        company=company,
        category=category,
        query=query
    )
    return json.dumps(contacts)

@tool
async def get_unique_companies_tool() -> str:
    """
    Retrieve a directory of unique companies stored in the platform, along with the contact count and member list for each organization.
    """
    contacts = await platform_client.get_all_contacts()
    companies_map: Dict[str, List[str]] = {}
    for c in contacts:
        company_name = c.get("company")
        if company_name:
            if company_name not in companies_map:
                companies_map[company_name] = []
            companies_map[company_name].append(c["name"])

    result = [
        {"company": comp, "contact_count": len(members), "members": members}
        for comp, members in companies_map.items()
    ]
    return json.dumps(result)

@tool
async def get_platform_stats_tool() -> str:
    """
    Retrieve platform analytics statistics (total contacts, companies, work vs. personal counts).
    """
    stats = await platform_client.get_stats()
    return json.dumps(stats)

@tool
async def validate_contact_emails_tool() -> str:
    """
    Scan all contacts to validate email address formats and identify any invalid email entries.
    """
    contacts = await platform_client.get_all_contacts()
    invalid_contacts = [c for c in contacts if not c.get("is_valid", True)]
    return json.dumps({
        "total_scanned": len(contacts),
        "invalid_count": len(invalid_contacts),
        "invalid_contacts": invalid_contacts
    })

@tool
async def create_contact_tool(
    name: str,
    email: str,
    phone: str,
    company: Optional[str] = None,
    category: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Create a new contact entry in the Contact Book Platform.
    """
    result = await platform_client.create_contact(
        name=name,
        email=email,
        phone=phone,
        company=company,
        category=category,
        notes=notes
    )
    if result:
        return json.dumps({"status": "success", "contact": result})
    return json.dumps({"status": "error", "message": "Failed to create contact."})

@tool
async def update_contact_tool(
    contact_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    category: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Update an existing contact's details by their unique ID.
    """
    result = await platform_client.update_contact(
        contact_id=contact_id,
        name=name,
        email=email,
        phone=phone,
        company=company,
        category=category,
        notes=notes
    )
    if result:
        return json.dumps({"status": "success", "contact": result})
    return json.dumps({"status": "error", "message": f"Failed to update contact {contact_id}."})

@tool
async def delete_contact_tool(contact_id: str) -> str:
    """
    Delete a contact by their unique ID.
    """
    success = await platform_client.delete_contact(contact_id)
    if success:
        return json.dumps({"status": "success", "message": f"Contact {contact_id} deleted."})
    return json.dumps({"status": "error", "message": f"Failed to delete contact {contact_id}."})

ALL_TOOLS = [
    list_contacts_tool,
    get_unique_companies_tool,
    get_platform_stats_tool,
    validate_contact_emails_tool,
    create_contact_tool,
    update_contact_tool,
    delete_contact_tool
]
