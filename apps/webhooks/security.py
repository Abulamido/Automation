"""
Webhook security utilities.

Provides signature verification for incoming webhooks from:
- Meta WhatsApp Business API
- Paystack

All webhooks should verify signatures before processing.
"""
import hmac
import hashlib
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_whatsapp_signature(payload: bytes, signature_header: str) -> bool:
    """
    Verify the X-Hub-Signature-256 header from Meta.
    
    Meta signs webhook payloads with your app secret using HMAC SHA-256.
    The signature is sent as: sha256=<hex_digest>
    
    Args:
        payload: Raw request body bytes
        signature_header: Value of X-Hub-Signature-256 header
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header")
        return False
    
    app_secret = settings.WHATSAPP_APP_SECRET
    if not app_secret:
        logger.warning("WHATSAPP_APP_SECRET not configured")
        return False
    
    try:
        # Extract the signature from "sha256=xxx" format
        if signature_header.startswith('sha256='):
            expected_signature = signature_header[7:]
        else:
            expected_signature = signature_header
        
        # Compute HMAC SHA-256
        computed_hmac = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        )
        computed_signature = computed_hmac.hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        if hmac.compare_digest(expected_signature, computed_signature):
            return True
        else:
            logger.warning("WhatsApp signature mismatch")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying WhatsApp signature: {e}")
        return False


def verify_paystack_signature(payload: bytes, signature_header: str) -> bool:
    """
    Verify the x-paystack-signature header from Paystack.
    
    Paystack signs webhook payloads with your secret key using HMAC SHA-512.
    
    Args:
        payload: Raw request body bytes
        signature_header: Value of x-paystack-signature header
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing x-paystack-signature header")
        return False
    
    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        logger.warning("PAYSTACK_SECRET_KEY not configured")
        return False
    
    try:
        # Compute HMAC SHA-512
        computed_hmac = hmac.new(
            secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        )
        computed_signature = computed_hmac.hexdigest()
        
        # Constant-time comparison
        if hmac.compare_digest(signature_header, computed_signature):
            return True
        else:
            logger.warning("Paystack signature mismatch")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying Paystack signature: {e}")
        return False
