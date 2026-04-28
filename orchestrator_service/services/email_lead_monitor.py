"""
DEV-34 Part 2: Email Lead Monitor — Meta Ads → Email → CRM
Monitors an IMAP inbox for Meta Ads lead notification emails and auto-creates leads.
Backup channel when the Meta webhook fails.

DEV-46 additions:
- _load_config_from_db: reads per-tenant IMAP config from email_monitor_config table
- check_new_emails: reloads DB config before each check; updates last_check_at
- _create_lead: blacklist check before CRM insert (G4)
"""

import os
import re
import imaplib
import email
import asyncio
import logging
from email.header import decode_header
from html.parser import HTMLParser
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from db import db

logger = logging.getLogger("email_lead_monitor")


class _HTMLTextExtractor(HTMLParser):
    """Simple HTML to text converter for email body parsing."""

    def __init__(self):
        super().__init__()
        self._text_parts: List[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        if tag in ("br", "p", "div", "tr", "li"):
            self._text_parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self._text_parts)


def _html_to_text(html_content: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()


def _decode_mime_header(header_value: str) -> str:
    """Decode MIME-encoded email header."""
    if not header_value:
        return ""
    parts = decode_header(header_value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _get_email_body(msg: email.message.Message) -> str:
    """Extract the email body as plain text (prefer HTML, fallback to plain)."""
    html_body = ""
    plain_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html_body = payload.decode(charset, errors="replace")
            elif content_type == "text/plain" and not plain_body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    plain_body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            content_type = msg.get_content_type()
            if content_type == "text/html":
                html_body = payload.decode(charset, errors="replace")
            else:
                plain_body = payload.decode(charset, errors="replace")

    if html_body:
        return _html_to_text(html_body)
    return plain_body


# ---------------------------------------------------------------------------
# Lead data extraction patterns
# ---------------------------------------------------------------------------

# Common patterns in Meta lead notification emails
_PATTERNS = {
    "name": [
        re.compile(r"(?:Nombre|Name|Full\s*Name)\s*[:\-]?\s*(.+)", re.IGNORECASE),
        re.compile(r"(?:Nombre completo)\s*[:\-]?\s*(.+)", re.IGNORECASE),
    ],
    "phone": [
        re.compile(r"(?:Tel[eé]fono|Phone|Whatsapp|N[uú]mero|phone_number)\s*[:\-]?\s*([\+\d\s\-\(\)]{7,20})", re.IGNORECASE),
    ],
    "email": [
        re.compile(r"(?:Email|Correo|E-mail)\s*[:\-]?\s*([\w.\-+]+@[\w.\-]+\.\w+)", re.IGNORECASE),
    ],
    "form_name": [
        re.compile(r"(?:Form(?:ulario)?|Form\s*Name)\s*[:\-]?\s*(.+)", re.IGNORECASE),
        re.compile(r"(?:Instant\s*Form)\s*[:\-]?\s*(.+)", re.IGNORECASE),
    ],
    "campaign": [
        re.compile(r"(?:Campa[ñn]a|Campaign)\s*[:\-]?\s*(.+)", re.IGNORECASE),
        re.compile(r"(?:Ad\s*Set|Conjunto)\s*[:\-]?\s*(.+)", re.IGNORECASE),
    ],
}


def _extract_lead_data(text: str) -> Dict[str, Optional[str]]:
    """
    Extract lead fields from the email body text.
    Returns dict with keys: name, phone, email, form_name, campaign.
    """
    result: Dict[str, Optional[str]] = {
        "name": None,
        "phone": None,
        "email": None,
        "form_name": None,
        "campaign": None,
    }

    lines = text.split("\n")
    full_text = text

    for field, patterns in _PATTERNS.items():
        for pattern in patterns:
            # Try line-by-line first (more accurate)
            for line in lines:
                m = pattern.search(line.strip())
                if m:
                    result[field] = m.group(1).strip()
                    break
            if result[field]:
                break
            # Fallback: full text
            m = pattern.search(full_text)
            if m:
                result[field] = m.group(1).strip()

    # Fallback email extraction from full body if not found
    if not result["email"]:
        email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w{2,}", full_text)
        if email_match:
            val = email_match.group(0)
            # Skip known Meta/Facebook emails
            if "facebookmail" not in val.lower() and "facebook.com" not in val.lower():
                result["email"] = val

    return result


class EmailLeadMonitor:
    """
    Connects to an IMAP inbox and processes Meta Ads lead notification emails,
    creating leads in the CRM via ensure_lead_exists.
    """

    def __init__(
        self,
        imap_host: Optional[str] = None,
        imap_user: Optional[str] = None,
        imap_password: Optional[str] = None,
        imap_folder: Optional[str] = None,
        imap_port: Optional[int] = None,
        tenant_id: int = 1,
    ):
        self.imap_host = imap_host or os.getenv("IMAP_HOST", "")
        self.imap_user = imap_user or os.getenv("IMAP_USER", "")
        self.imap_password = imap_password or os.getenv("IMAP_PASSWORD", "")
        self.imap_folder = imap_folder or os.getenv("IMAP_FOLDER", "INBOX")
        self.imap_port = imap_port or int(os.getenv("IMAP_PORT", "993"))
        self.tenant_id = tenant_id
        self._polling_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Config: load from DB (DEV-46 G2)
    # ------------------------------------------------------------------

    async def _load_config_from_db(self) -> None:
        """
        Load IMAP config from email_monitor_config table for self.tenant_id.
        Falls back to env vars if no DB config exists or DB is unavailable.
        """
        try:
            row = await db.fetchrow(
                "SELECT imap_host, imap_user, imap_password_encrypted, imap_port, imap_folder, "
                "polling_interval, active FROM email_monitor_config WHERE tenant_id = $1",
                self.tenant_id,
            )
            if row and row["imap_host"]:
                self.imap_host = row["imap_host"] or self.imap_host
                self.imap_user = row["imap_user"] or self.imap_user
                self.imap_password = row["imap_password_encrypted"] or self.imap_password
                self.imap_port = row["imap_port"] or self.imap_port
                self.imap_folder = row["imap_folder"] or self.imap_folder
                logger.info(f"Email monitor: config loaded from DB for tenant {self.tenant_id}")
        except Exception as e:
            logger.warning(f"Email monitor: could not load config from DB (using env vars): {e}")

    # ------------------------------------------------------------------
    # Core: check inbox
    # ------------------------------------------------------------------

    async def check_new_emails(self) -> int:
        """
        Connect to IMAP, search for UNSEEN Meta lead emails,
        parse and ingest leads, mark as SEEN.
        Returns the number of leads created/updated.

        DEV-46: Reloads DB config before each check; updates last_check_at after.
        """
        await self._load_config_from_db()

        if not self.imap_host or not self.imap_user:
            logger.warning("Email monitor: IMAP not configured (IMAP_HOST / IMAP_USER missing)")
            return 0

        leads_found = 0
        try:
            # imaplib is synchronous — run in executor to avoid blocking the event loop
            leads_found = await asyncio.get_event_loop().run_in_executor(
                None, self._sync_check_emails
            )
        except Exception as exc:
            logger.error(f"Email monitor error: {exc}", exc_info=True)

        # Update last_check_at in DB (best-effort)
        try:
            await db.execute(
                "UPDATE email_monitor_config SET last_check_at = NOW(), last_check_result = $1, "
                "updated_at = NOW() WHERE tenant_id = $2",
                f"{leads_found} lead(s) processed",
                self.tenant_id,
            )
        except Exception:
            pass  # Non-critical; table may not exist yet on first run

        return leads_found

    def _sync_check_emails(self) -> int:
        """Synchronous IMAP fetch — called inside run_in_executor."""
        leads_found = 0
        mail: Optional[imaplib.IMAP4_SSL] = None

        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.imap_user, self.imap_password)
            mail.select(self.imap_folder)
            logger.info(f"Email monitor: connected to {self.imap_host}, folder={self.imap_folder}")

            # Search for UNSEEN emails from facebookmail.com
            _, msg_ids_fb = mail.search(None, '(UNSEEN FROM "facebookmail.com")')
            # Also search for UNSEEN emails with "lead" in subject
            _, msg_ids_lead = mail.search(None, '(UNSEEN SUBJECT "lead")')

            # Merge unique IDs
            all_ids: set = set()
            for id_bytes in (msg_ids_fb[0], msg_ids_lead[0]):
                if id_bytes:
                    all_ids.update(id_bytes.split())

            if not all_ids:
                logger.info("Email monitor: no new Meta lead emails found")
                return 0

            logger.info(f"Email monitor: found {len(all_ids)} candidate emails")

            # Collect leads to create (will be processed async after)
            self._pending_leads: List[Dict] = []

            for msg_id in all_ids:
                try:
                    _, data = mail.fetch(msg_id, "(RFC822)")
                    if not data or not data[0] or not isinstance(data[0], tuple):
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    subject = _decode_mime_header(msg.get("Subject", ""))
                    sender = _decode_mime_header(msg.get("From", ""))

                    body = _get_email_body(msg)
                    lead_data = _extract_lead_data(body)

                    # Must have at least name or phone to be useful
                    if not lead_data["name"] and not lead_data["phone"]:
                        logger.debug(f"Email monitor: skipping email '{subject}' — no lead data extracted")
                        # Still mark as seen so we don't re-process
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                        continue

                    lead_data["_subject"] = subject
                    lead_data["_sender"] = sender
                    self._pending_leads.append(lead_data)

                    # Mark as SEEN
                    mail.store(msg_id, "+FLAGS", "\\Seen")

                    logger.info(
                        f"Email monitor: extracted lead — name={lead_data['name']}, "
                        f"phone={lead_data['phone']}, email={lead_data['email']}, "
                        f"form={lead_data['form_name']}, campaign={lead_data['campaign']}"
                    )

                except Exception as e:
                    logger.error(f"Email monitor: error processing email {msg_id}: {e}")
                    # Mark as seen to avoid infinite retries
                    try:
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                    except Exception:
                        pass

            leads_found = len(self._pending_leads)

        except imaplib.IMAP4.error as e:
            logger.error(f"Email monitor IMAP error: {e}")
        except Exception as e:
            logger.error(f"Email monitor unexpected error: {e}", exc_info=True)
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except Exception:
                    pass

        # Now create the leads asynchronously
        if hasattr(self, "_pending_leads") and self._pending_leads:
            loop = asyncio.get_event_loop()
            for ld in self._pending_leads:
                loop.create_task(self._create_lead(ld))

        return leads_found

    async def _create_lead(self, lead_data: Dict) -> None:
        """Create or update a lead in the CRM from parsed email data."""
        try:
            name = lead_data.get("name") or "Lead Email"
            phone = lead_data.get("phone") or ""
            lead_email = lead_data.get("email") or ""
            form_name = lead_data.get("form_name") or ""
            campaign = lead_data.get("campaign") or ""

            # Normalize phone — remove spaces, dashes, parentheses
            phone_clean = re.sub(r"[\s\-\(\)]", "", phone) if phone else ""

            # If no phone, use email as phone placeholder (ensure_lead_exists requires phone)
            identifier = phone_clean if phone_clean else lead_email
            if not identifier:
                logger.warning(f"Email monitor: lead '{name}' has no phone or email, skipping CRM insert")
                return

            # DEV-46 G4: Blacklist check before lead creation
            try:
                from services.blacklist_service import BlacklistService
                _bl = BlacklistService()
                is_blocked, bl_reason = await _bl.is_blacklisted_normalized(
                    tenant_id=self.tenant_id,
                    phone=phone_clean or None,
                    email=lead_email or None,
                )
                if is_blocked:
                    logger.info(
                        f"Email monitor: skipping blacklisted lead '{name}' "
                        f"(phone={phone_clean}, email={lead_email}, reason={bl_reason})"
                    )
                    await _bl.log_attempt(
                        tenant_id=self.tenant_id,
                        value=phone_clean or lead_email,
                        type="phone" if phone_clean else "email",
                        source="email_monitor",
                        payload=lead_data,
                    )
                    return
            except Exception as bl_err:
                logger.warning(f"Email monitor: blacklist check failed (proceeding): {bl_err}")

            # Build referral-like attribution for ensure_lead_exists
            referral = None
            if campaign or form_name:
                referral = {
                    "source": "email_meta",
                    "headline": form_name,
                    "body": f"Campaign: {campaign}" if campaign else "",
                }

            lead = await db.ensure_lead_exists(
                tenant_id=self.tenant_id,
                phone_number=identifier,
                customer_name=name,
                source="email_meta",
                referral=referral,
            )

            # Update email field if we have it and lead was created
            if lead and lead_email:
                try:
                    await db.execute(
                        "UPDATE leads SET email = COALESCE(NULLIF(email, ''), $1), updated_at = NOW() WHERE id = $2",
                        lead_email, lead["id"],
                    )
                except Exception as e:
                    logger.warning(f"Email monitor: could not update email for lead {lead.get('id')}: {e}")

            # Update campaign/form metadata
            if lead and (campaign or form_name):
                try:
                    meta_updates = []
                    meta_values = []
                    idx = 1
                    if campaign:
                        meta_updates.append(f"meta_campaign_id = ${idx}")
                        meta_values.append(campaign)
                        idx += 1
                    if form_name:
                        meta_updates.append(f"meta_ad_headline = ${idx}")
                        meta_values.append(form_name)
                        idx += 1
                    if meta_updates:
                        meta_updates.append(f"lead_source = 'META_ADS'")
                        meta_updates.append("updated_at = NOW()")
                        query = f"UPDATE leads SET {', '.join(meta_updates)} WHERE id = ${idx}"
                        meta_values.append(lead["id"])
                        await db.execute(query, *meta_values)
                except Exception as e:
                    logger.warning(f"Email monitor: could not update meta fields: {e}")

            logger.info(f"Email monitor: lead ingested — id={lead.get('id') if lead else '?'}, phone={identifier}")

        except Exception as e:
            logger.error(f"Email monitor: error creating lead from email data: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def start_polling(self, interval_seconds: int = 120) -> None:
        """Start background polling loop."""
        if self._polling_task and not self._polling_task.done():
            logger.warning("Email monitor: polling already running")
            return

        self._polling_task = asyncio.create_task(self._poll_loop(interval_seconds))
        logger.info(f"Email monitor: polling started (every {interval_seconds}s)")

    async def _poll_loop(self, interval: int) -> None:
        """Internal polling loop — runs indefinitely."""
        while True:
            try:
                count = await self.check_new_emails()
                if count > 0:
                    logger.info(f"Email monitor: {count} leads processed in this cycle")
            except Exception as e:
                logger.error(f"Email monitor poll error: {e}", exc_info=True)
            await asyncio.sleep(interval)

    def stop_polling(self) -> None:
        """Cancel the polling task."""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            logger.info("Email monitor: polling stopped")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
email_lead_monitor = EmailLeadMonitor()
