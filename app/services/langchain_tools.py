import json
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from app.services.platform_client import platform_client

# Personal Contact Tools
@tool
async def list_contacts_tool(
    name: Optional[str] = None,
    email: Optional[str] = None,
    query: Optional[str] = None
) -> str:
    """
    Search and filter personal contacts from the Contact Book Platform.
    """
    contacts = await platform_client.get_all_contacts(
        name=name,
        email=email,
        query=query
    )
    return json.dumps(contacts)

@tool
async def create_contact_tool(
    name: str,
    email: str,
    phone: str,
    notes: Optional[str] = None
) -> str:
    """
    Create a new personal contact entry in the Contact Book Platform.
    """
    result = await platform_client.create_contact(
        name=name,
        email=email,
        phone=phone,
        notes=notes
    )
    if isinstance(result, dict) and result.get("error"):
        return json.dumps(result)
    if result:
        return json.dumps({"status": "success", "contact": result})
    return json.dumps({"status": "error", "message": "Failed to create contact."})

@tool
async def update_contact_tool(
    contact_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Update an existing personal contact's details by ID.
    """
    result = await platform_client.update_contact(
        contact_id=contact_id,
        name=name,
        email=email,
        phone=phone,
        notes=notes
    )
    if isinstance(result, dict) and result.get("error"):
        return json.dumps(result)
    if result:
        return json.dumps({"status": "success", "contact": result})
    return json.dumps({"status": "error", "message": f"Failed to update contact {contact_id}."})

@tool
async def delete_contact_tool(contact_id: str) -> str:
    """
    Delete a personal contact by ID.
    """
    success = await platform_client.delete_contact(contact_id)
    if isinstance(success, dict) and success.get("error"):
        return json.dumps(success)
    if success:
        return json.dumps({"status": "success", "message": f"Contact {contact_id} deleted."})
    return json.dumps({"status": "error", "message": f"Failed to delete contact {contact_id}."})

# Company Contact Tools
@tool
async def list_companies_tool(
    name: Optional[str] = None,
    company_email: Optional[str] = None,
    location: Optional[str] = None,
    query: Optional[str] = None
) -> str:
    """
    Search and filter company entries (company contacts) stored in the platform.
    """
    companies = await platform_client.get_all_companies(
        name=name,
        company_email=company_email,
        location=location,
        query=query
    )
    return json.dumps(companies)

@tool
async def create_company_tool(
    name: str,
    company_email: str,
    phone: str,
    location: str,
    notes: Optional[str] = None
) -> str:
    """
    Create a new company contact entry in the Contact Book Platform.
    """
    result = await platform_client.create_company(
        name=name,
        company_email=company_email,
        phone=phone,
        location=location,
        notes=notes
    )
    if isinstance(result, dict) and result.get("error"):
        return json.dumps(result)
    if result:
        return json.dumps({"status": "success", "company": result})
    return json.dumps({"status": "error", "message": "Failed to create company contact."})

@tool
async def update_company_tool(
    company_id: str,
    name: Optional[str] = None,
    company_email: Optional[str] = None,
    phone: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Update an existing company contact entry by ID.
    """
    result = await platform_client.update_company(
        company_id=company_id,
        name=name,
        company_email=company_email,
        phone=phone,
        location=location,
        notes=notes
    )
    if isinstance(result, dict) and result.get("error"):
        return json.dumps(result)
    if result:
        return json.dumps({"status": "success", "company": result})
    return json.dumps({"status": "error", "message": f"Failed to update company {company_id}."})

@tool
async def delete_company_tool(company_id: str) -> str:
    """
    Delete a company contact entry by ID.
    """
    success = await platform_client.delete_company(company_id)
    if isinstance(success, dict) and success.get("error"):
        return json.dumps(success)
    if success:
        return json.dumps({"status": "success", "message": f"Company contact {company_id} deleted."})
    return json.dumps({"status": "error", "message": f"Failed to delete company {company_id}."})

@tool
async def get_platform_stats_tool() -> str:
    """
    Retrieve platform totals for personal contacts and company contacts.
    """
    stats = await platform_client.get_stats()
    return json.dumps(stats)

ALL_TOOLS = [
    list_contacts_tool,
    create_contact_tool,
    update_contact_tool,
    delete_contact_tool,
    list_companies_tool,
    create_company_tool,
    update_company_tool,
    delete_company_tool,
    get_platform_stats_tool
]
