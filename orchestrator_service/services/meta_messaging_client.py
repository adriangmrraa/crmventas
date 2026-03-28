"""
Meta Graph API Messaging Client.

Handles sending messages via Meta's direct APIs:
- WhatsApp Cloud API (graph.facebook.com/{phone_number_id}/messages)
- Facebook Messenger (graph.facebook.com/me/messages with page token)
- Instagram DMs (graph.facebook.com/me/messages with page token)
"""
import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaMessagingClient:
    """Stateless helper — every method receives the credentials it needs."""

    def __init__(self, timeout: float = 20.0):
        self._timeout = httpx.Timeout(timeout, connect=5.0)

    # ------------------------------------------------------------------
    # Internal HTTP helper with retry
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _post(self, url: str, json_data: dict, headers: dict) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=json_data, headers=headers)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # WhatsApp Cloud API
    # ------------------------------------------------------------------
    async def send_whatsapp_text(
        self,
        phone_number_id: str,
        to: str,
        text: str,
        access_token: str,
    ) -> dict:
        """Send a text message via WhatsApp Cloud API."""
        url = f"{GRAPH_BASE_URL}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": True, "body": text},
        }
        logger.info(
            "meta_wa_send_text phone_number_id=%s to=%s text_preview=%.30s",
            phone_number_id, to, text,
        )
        return await self._post(url, payload, headers)

    async def send_whatsapp_image(
        self,
        phone_number_id: str,
        to: str,
        image_url: str,
        access_token: str,
        caption: Optional[str] = None,
    ) -> dict:
        """Send an image message via WhatsApp Cloud API."""
        url = f"{GRAPH_BASE_URL}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        image_obj: dict = {"link": image_url}
        if caption:
            image_obj["caption"] = caption
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image_obj,
        }
        logger.info(
            "meta_wa_send_image phone_number_id=%s to=%s url=%.60s",
            phone_number_id, to, image_url,
        )
        return await self._post(url, payload, headers)

    async def send_whatsapp_template(
        self,
        phone_number_id: str,
        to: str,
        template_name: str,
        language: str,
        components: list,
        access_token: str,
    ) -> dict:
        """Send a template message via WhatsApp Cloud API."""
        url = f"{GRAPH_BASE_URL}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            },
        }
        logger.info(
            "meta_wa_send_template phone_number_id=%s to=%s template=%s",
            phone_number_id, to, template_name,
        )
        return await self._post(url, payload, headers)

    # ------------------------------------------------------------------
    # Facebook Messenger
    # ------------------------------------------------------------------
    async def send_messenger_text(
        self,
        page_id: str,
        recipient_psid: str,
        text: str,
        page_token: str,
    ) -> dict:
        """Send a text message via Facebook Messenger Send API."""
        url = f"{GRAPH_BASE_URL}/{page_id}/messages"
        headers = {
            "Authorization": f"Bearer {page_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": recipient_psid},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
        }
        logger.info(
            "meta_messenger_send page_id=%s recipient=%s text_preview=%.30s",
            page_id, recipient_psid, text,
        )
        return await self._post(url, payload, headers)

    async def send_messenger_image(
        self,
        page_id: str,
        recipient_psid: str,
        image_url: str,
        page_token: str,
    ) -> dict:
        """Send an image attachment via Facebook Messenger."""
        url = f"{GRAPH_BASE_URL}/{page_id}/messages"
        headers = {
            "Authorization": f"Bearer {page_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": recipient_psid},
            "messaging_type": "RESPONSE",
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"url": image_url, "is_reusable": True},
                }
            },
        }
        logger.info(
            "meta_messenger_send_image page_id=%s recipient=%s url=%.60s",
            page_id, recipient_psid, image_url,
        )
        return await self._post(url, payload, headers)

    # ------------------------------------------------------------------
    # Instagram DM
    # ------------------------------------------------------------------
    async def send_instagram_text(
        self,
        page_id: str,
        recipient_psid: str,
        text: str,
        page_token: str,
    ) -> dict:
        """Send a text message via Instagram Messaging API (uses same Send API)."""
        url = f"{GRAPH_BASE_URL}/{page_id}/messages"
        headers = {
            "Authorization": f"Bearer {page_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": recipient_psid},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
        }
        logger.info(
            "meta_instagram_send page_id=%s recipient=%s text_preview=%.30s",
            page_id, recipient_psid, text,
        )
        return await self._post(url, payload, headers)

    async def send_instagram_image(
        self,
        page_id: str,
        recipient_psid: str,
        image_url: str,
        page_token: str,
    ) -> dict:
        """Send an image via Instagram DM."""
        url = f"{GRAPH_BASE_URL}/{page_id}/messages"
        headers = {
            "Authorization": f"Bearer {page_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": recipient_psid},
            "messaging_type": "RESPONSE",
            "message": {
                "attachment": {
                    "type": "image",
                    "payload": {"url": image_url, "is_reusable": True},
                }
            },
        }
        logger.info(
            "meta_instagram_send_image page_id=%s recipient=%s url=%.60s",
            page_id, recipient_psid, image_url,
        )
        return await self._post(url, payload, headers)

    # ------------------------------------------------------------------
    # Read Receipts (WhatsApp Cloud API)
    # ------------------------------------------------------------------
    async def mark_as_read(
        self,
        phone_number_id: str,
        message_id: str,
        access_token: str,
    ) -> dict:
        """Mark a WhatsApp message as read (blue ticks)."""
        url = f"{GRAPH_BASE_URL}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        logger.info(
            "meta_wa_mark_read phone_number_id=%s message_id=%s",
            phone_number_id, message_id,
        )
        return await self._post(url, payload, headers)


# Module-level singleton
meta_client = MetaMessagingClient()
