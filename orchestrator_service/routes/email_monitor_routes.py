"""
DEV-34 Part 2 + DEV-46: Email Monitor Routes
CEO-only endpoints for email inbox monitoring and per-tenant IMAP configuration.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.security import verify_admin_token, get_resolved_tenant_id
from services.email_lead_monitor import email_lead_monitor
from db import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/core/email-monitor", tags=["Email Lead Monitor"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EmailMonitorConfigIn(BaseModel):
    imap_host: Optional[str] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None  # stored as imap_password_encrypted (plaintext for now)
    imap_port: Optional[int] = 993
    imap_folder: Optional[str] = "INBOX"
    polling_interval: Optional[int] = 300
    active: Optional[bool] = True


# ---------------------------------------------------------------------------
# Manual trigger
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

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

    # Fetch last_check_at from DB
    last_check_at = None
    last_check_result = None
    try:
        row = await db.fetchrow(
            "SELECT last_check_at, last_check_result FROM email_monitor_config WHERE tenant_id = $1",
            email_lead_monitor.tenant_id,
        )
        if row:
            last_check_at = row["last_check_at"].isoformat() if row["last_check_at"] else None
            last_check_result = row["last_check_result"]
    except Exception:
        pass

    return {
        "configured": bool(email_lead_monitor.imap_host and email_lead_monitor.imap_user),
        "imap_host": email_lead_monitor.imap_host or "(not set)",
        "imap_folder": email_lead_monitor.imap_folder,
        "polling_active": polling_active,
        "tenant_id": email_lead_monitor.tenant_id,
        "last_check_at": last_check_at,
        "last_check_result": last_check_result,
    }


# ---------------------------------------------------------------------------
# Per-tenant IMAP config: GET / PUT (DEV-46 G2)
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_email_monitor_config(
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    Retrieve the stored IMAP configuration for the current tenant.
    CEO only. Password is not returned.
    """
    if user_data.role != "ceo":
        raise HTTPException(status_code=403, detail="CEO only")
    try:
        row = await db.fetchrow(
            "SELECT imap_host, imap_user, imap_port, imap_folder, polling_interval, active, "
            "last_check_at, last_check_result FROM email_monitor_config WHERE tenant_id = $1",
            tenant_id,
        )
    except Exception as e:
        logger.error(f"Error fetching email monitor config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch config")

    if not row:
        # Return defaults (no config saved yet)
        return {
            "configured": False,
            "imap_host": "",
            "imap_user": "",
            "imap_port": 993,
            "imap_folder": "INBOX",
            "polling_interval": 300,
            "active": False,
            "last_check_at": None,
            "last_check_result": None,
        }

    return {
        "configured": bool(row["imap_host"] and row["imap_user"]),
        "imap_host": row["imap_host"] or "",
        "imap_user": row["imap_user"] or "",
        "imap_port": row["imap_port"] or 993,
        "imap_folder": row["imap_folder"] or "INBOX",
        "polling_interval": row["polling_interval"] or 300,
        "active": row["active"] if row["active"] is not None else True,
        "last_check_at": row["last_check_at"].isoformat() if row["last_check_at"] else None,
        "last_check_result": row["last_check_result"],
    }


@router.put("/config")
async def update_email_monitor_config(
    payload: EmailMonitorConfigIn,
    user_data=Depends(verify_admin_token),
    tenant_id: int = Depends(get_resolved_tenant_id),
):
    """
    Save IMAP configuration for the current tenant.
    CEO only. Upserts into email_monitor_config table.
    """
    if user_data.role != "ceo":
        raise HTTPException(status_code=403, detail="CEO only")
    try:
        await db.execute(
            """
            INSERT INTO email_monitor_config
                (tenant_id, imap_host, imap_user, imap_password_encrypted, imap_port,
                 imap_folder, polling_interval, active, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT (tenant_id) DO UPDATE SET
                imap_host               = EXCLUDED.imap_host,
                imap_user               = EXCLUDED.imap_user,
                imap_password_encrypted = COALESCE(NULLIF(EXCLUDED.imap_password_encrypted, ''), email_monitor_config.imap_password_encrypted),
                imap_port               = EXCLUDED.imap_port,
                imap_folder             = EXCLUDED.imap_folder,
                polling_interval        = EXCLUDED.polling_interval,
                active                  = EXCLUDED.active,
                updated_at              = NOW()
            """,
            tenant_id,
            payload.imap_host,
            payload.imap_user,
            payload.imap_password or "",
            payload.imap_port or 993,
            payload.imap_folder or "INBOX",
            payload.polling_interval or 300,
            payload.active if payload.active is not None else True,
        )
    except Exception as e:
        logger.error(f"Error saving email monitor config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not save config")

    # Reload config into the running singleton
    await email_lead_monitor._load_config_from_db()

    return {"status": "ok", "message": "Email monitor configuration saved"}


# ---------------------------------------------------------------------------
# Connection test
# ---------------------------------------------------------------------------

@router.post("/test-connection")
async def test_email_connection(user_data=Depends(verify_admin_token)):
    """
    Test the IMAP connection with the current (DB or env) configuration.
    CEO only. Does NOT process any emails.
    """
    if user_data.role != "ceo":
        raise HTTPException(status_code=403, detail="CEO only")

    import asyncio
    import imaplib

    await email_lead_monitor._load_config_from_db()

    if not email_lead_monitor.imap_host or not email_lead_monitor.imap_user:
        return {"status": "error", "message": "IMAP host and user are required"}

    def _test_conn():
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(email_lead_monitor.imap_host, email_lead_monitor.imap_port)
            mail.login(email_lead_monitor.imap_user, email_lead_monitor.imap_password)
            mail.select(email_lead_monitor.imap_folder)
            typ, data = mail.search(None, "ALL")
            total = len(data[0].split()) if data and data[0] else 0
            return {"status": "ok", "message": f"Connected. {total} total messages in {email_lead_monitor.imap_folder}."}
        except imaplib.IMAP4.error as e:
            return {"status": "error", "message": f"IMAP error: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except Exception:
                    pass

    try:
        result = await asyncio.get_event_loop().run_in_executor(None, _test_conn)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
