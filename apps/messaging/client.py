"""
WhatsApp Business Cloud API Client.

Handles outbound messaging to WhatsApp users via Meta's REST API.
Supports text messages and template messages (for out-of-window notifications).
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Client for interacting with the Meta WhatsApp Business Cloud API.
    
    This client handles:
    - Sending text messages
    - Sending template messages
    - Proper error handling and logging
    """

    def __init__(self):
        """Initialize client with credentials from settings."""
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.api_version = getattr(settings, 'WHATSAPP_API_VERSION', 'v18.0')
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"

    def _get_headers(self) -> dict:
        """Get standard headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def send_text(self, to: str, message: str) -> dict:
        """
        Send a standard text message.
        
        Note: This only works if the user has messaged the bot within 24 hours.
        For messages outside this window, use send_template().
        
        Args:
            to: User's WhatsApp ID or phone number
            message: Text content to send
            
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }

        try:
            logger.info(f"Sending WhatsApp text to {to}")
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"WhatsApp API response: {data}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response body: {e.response.text}")
            raise

    def send_template(self, to: str, template_name: str, language_code: str = "en_US", 
                      components: list = None) -> dict:
        """
        Send a template message (required for notifications outside 24h window).
        
        Args:
            to: User's WhatsApp ID
            template_name: Name of the approved template
            language_code: Language code (default en_US)
            components: List of component objects for variables
            
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            }
        }

        if components:
            payload["template"]["components"] = components

        try:
            logger.info(f"Sending WhatsApp template '{template_name}' to {to}")
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp template: {e}")
            raise


# Singleton instance
whatsapp_client = WhatsAppClient()
