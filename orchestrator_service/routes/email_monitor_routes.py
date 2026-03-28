"""
DEV-34 Part 2: Email Monitor Routes
CEO-only endpoint to manually trigger email inbox check for Meta leads.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends

from core.security import verify_admin_token
from services.email_lead_monitor import email_lead_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/core/email-monitor", tags=["Email Lead Monitor"])


@router.post("/check-now")
async def check_email_inbox_now(user_data=Depends(verify_admin_token)):
    """
    Manually trigger an immediate check of the IMAP inbox for Meta lead emails.
    CEO only.
    """
    if user_data.role != "ceo":
        raise HTTPException(status_code=403, detail="CEO only")

    try:
        leads_found = await email_lead_monitor.check_new_emails()
        return {
            "status": "ok",
            "leads_found": leads_found,
            "message": f"{leads_found} lead(s) processed from email inbox",
        }
    except Exception as e:
        logger.error(f"Manual email check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Email check failed: {str(e)}")


@router.get("/status")
async def email_monitor_status(user_data=Depends(verify_admin_token)):
    """
    Get current status of the email lead monitor.
    CEO only.
    """
    if user_data.role != "ceo":
        raise HTTPException(status_code=403, detail="CEO only")

    polling_active = (
        email_lead_monitor._polling_task is not None
        and not email_lead_monitor._polling_task.done()
    )

    return {
        "configured": bool(email_lead_monitor.imap_host and email_lead_monitor.imap_user),
        "imap_host": email_lead_monitor.imap_host or "(not set)",
        "imap_folder": email_lead_monitor.imap_folder,
        "polling_active": polling_active,
        "tenant_id": email_lead_monitor.tenant_id,
    }
