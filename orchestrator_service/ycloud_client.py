import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional
import logging

logger = logging.getLogger("ycloud_client")

class YCloudClient:
    BASE_URL = "https://api.ycloud.com/v2"

    def __init__(self, api_key: str, business_number: str = None):
        self.api_key = api_key
        self.business_number = business_number
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def _post(self, endpoint: str, json_data: dict, correlation_id: str):
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            url = f"{self.BASE_URL}{endpoint}"
            response = await client.post(url, json=json_data, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def send_text(self, to: str, text: str, correlation_id: str):
        payload = {
            "from": self.business_number,
            "to": to,
            "type": "text",
            "text": {"body": text, "preview_url": True}
        }
        logger.info(f"Sending YCloud text to {to}, correlation_id={correlation_id}")
        return await self._post("/whatsapp/messages/sendDirectly", payload, correlation_id)

    async def send_template(self, to: str, template_name: str, language_code: str, components: list, correlation_id: str):
        """Sends a WhatsApp message using a template."""
        payload = {
            "from": self.business_number,
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components
            }
        }
        logger.info(f"Sending YCloud template {template_name} to {to}, correlation_id={correlation_id}")
        return await self._post("/whatsapp/messages/sendDirectly", payload, correlation_id)
