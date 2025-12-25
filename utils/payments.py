"""
Paystack API Integration.

Handles transaction initialization and verification for order payments.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackClient:
    """
    Client for interacting with the Paystack Payment Gateway API.
    
    Handles:
    - Initiating transactions (getting payment URL)
    - Verifying transaction status
    """

    def __init__(self):
        """Initialize client with secrets from settings."""
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = getattr(settings, 'PAYSTACK_BASE_URL', 'https://api.paystack.co')

    def _get_headers(self) -> dict:
        """Get standard headers for Paystack API."""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(self, email: str, amount_minor: int, 
                               reference: str, metadata: dict = None) -> dict:
        """
        Initialize a Paystack transaction and get an authorization URL.
        
        Args:
            email: Customer email (required by Paystack)
            amount_minor: Amount in minor units (e.g., kobo)
            reference: Unique transaction reference (usually our order reference)
            metadata: Optional metadata for tracking/webhooks
            
        Returns:
            Dict containing 'authorization_url' and 'reference'
        """
        url = f"{self.base_url}/transaction/initialize"
        
        payload = {
            "email": email,
            "amount": amount_minor,
            "reference": reference,
            "metadata": metadata or {}
        }

        try:
            logger.info(f"Initializing Paystack transaction for ref: {reference}")
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return data.get('data')
            else:
                raise ValueError(f"Paystack initialization failed: {data.get('message')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API error: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response body: {e.response.text}")
            raise

    def verify_transaction(self, reference: str) -> dict:
        """
        Verify the status of a transaction by reference.
        
        Args:
            reference: Paystack reference or order reference
            
        Returns:
            Dict containing transaction status and details
        """
        url = f"{self.base_url}/transaction/verify/{reference}"

        try:
            logger.info(f"Verifying Paystack transaction ref: {reference}")
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status'):
                return data.get('data')
            else:
                logger.warning(f"Paystack verification failed: {data.get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification error: {e}")
            return None


# Singleton instance
paystack_client = PaystackClient()
