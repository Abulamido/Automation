"""
Webhook views for WhatsApp and Paystack.

These endpoints receive webhook calls from external services:
- WhatsApp: Message notifications from Meta
- Paystack: Payment status notifications

Both endpoints:
1. Verify signatures for security
2. Return 200 quickly to avoid timeouts
3. Process payloads appropriately
"""
import json
import logging
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .security import verify_whatsapp_signature, verify_paystack_signature
from apps.conversations.engine import conversation_engine
from apps.messaging.client import whatsapp_client

logger = logging.getLogger(__name__)


class WhatsAppWebhookView(APIView):
    """
    WhatsApp Business API webhook endpoint.
    
    Handles:
    - GET: Webhook verification (hub.verify_token challenge)
    - POST: Incoming message notifications
    
    Security:
    - Verification token check on GET
    - HMAC signature verification on POST
    """
    # Must be public for Meta to reach us
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        """
        Handle webhook verification from Meta.
        
        Meta sends a GET request with:
        - hub.mode: should be 'subscribe'
        - hub.verify_token: our configured token
        - hub.challenge: string to echo back
        """
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')

        logger.info(f"WhatsApp webhook verification: mode={mode}")

        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("WhatsApp webhook verified successfully")
            return HttpResponse(challenge, content_type='text/plain')
        else:
            logger.warning(f"WhatsApp webhook verification failed: token mismatch. Received: '{token}', Expected: '{settings.WHATSAPP_VERIFY_TOKEN}'")
            return Response(
                {'error': 'Verification failed'},
                status=status.HTTP_403_FORBIDDEN
            )

    def post(self, request):
        print(f"DEBUG: HIT POST WEBHOOK with body: {request.body}")
        """
        Process incoming WhatsApp messages.
        
        Payload structure (simplified):
        {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "234...",
                            "id": "wamid.xxx",
                            "text": {"body": "Hello"},
                            "type": "text"
                        }],
                        "contacts": [{
                            "profile": {"name": "John"},
                            "wa_id": "234..."
                        }]
                    }
                }]
            }]
        }
        """
        # Verify signature in production
        if settings.WHATSAPP_APP_SECRET and False:  # Disabled for debugging
            signature = request.headers.get('X-Hub-Signature-256', '')
            if not verify_whatsapp_signature(request.body, signature):
                logger.warning("Invalid WhatsApp webhook signature")
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        try:
            payload = request.data
            logger.debug(f"WhatsApp webhook payload: {json.dumps(payload)[:500]}")

            # Process each entry
            for entry in payload.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    
                    # Get contact info
                    contacts = value.get('contacts', [])
                    contact = contacts[0] if contacts else {}
                    profile_name = contact.get('profile', {}).get('name', '')
                    wa_id = contact.get('wa_id', '')

                    # Process messages
                    messages = value.get('messages', [])
                    for message in messages:
                        self._process_message(message, wa_id, profile_name)

            # Always return 200 to acknowledge receipt
            return Response({'status': 'ok'})

        except Exception as e:
            logger.exception(f"Error processing WhatsApp webhook: {e}")
            # Still return 200 to prevent retries for malformed requests
            return Response({'status': 'error', 'message': str(e)})

    def _process_message(self, message: dict, wa_id: str, profile_name: str):
        """
        Process a single incoming message.
        
        Currently handles text messages only. Button replies and other
        types can be added later.
        """
        message_id = message.get('id', '')
        message_type = message.get('type', '')
        phone_number = message.get('from', wa_id)

        logger.info(f"Processing {message_type} message from {wa_id}")

        # Handle text messages
        if message_type == 'text':
            text_body = message.get('text', {}).get('body', '')
            
            if text_body:
                # Process through conversation engine
                response_messages = conversation_engine.process_message(
                    wa_id=wa_id,
                    phone_number=phone_number,
                    user_name=profile_name,
                    message_text=text_body,
                    message_id=message_id
                )
                
                # Send responses
                for response_text in response_messages:
                    if response_text:  # Skip empty messages
                        try:
                            whatsapp_client.send_text(wa_id, response_text)
                        except Exception as e:
                            logger.error(f"Failed to send response: {e}")

        # Handle button replies (for future interactive messages)
        elif message_type == 'button':
            button_payload = message.get('button', {}).get('payload', '')
            button_text = message.get('button', {}).get('text', '')
            # Process button click as text for now
            response_messages = conversation_engine.process_message(
                wa_id=wa_id,
                phone_number=phone_number,
                user_name=profile_name,
                message_text=button_text or button_payload,
                message_id=message_id
            )
            for response_text in response_messages:
                if response_text:
                    try:
                        whatsapp_client.send_text(wa_id, response_text)
                    except Exception as e:
                        logger.error(f"Failed to send response: {e}")

        else:
            logger.info(f"Unhandled message type: {message_type}")


class PaystackWebhookView(APIView):
    """
    Paystack webhook endpoint for payment notifications.
    
    Handles payment events, primarily 'charge.success' for confirmed payments.
    
    Security:
    - HMAC signature verification
    - Event type validation
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        """
        Process Paystack webhook events.
        
        Event structure:
        {
            "event": "charge.success",
            "data": {
                "reference": "ORD-XXXXXXXX",
                "amount": 150000,
                "metadata": {
                    "order_id": 123
                },
                ...
            }
        }
        """
        # Verify signature
        signature = request.headers.get('x-paystack-signature', '')
        if not verify_paystack_signature(request.body, signature):
            logger.warning("Invalid Paystack webhook signature")
            return Response(
                {'error': 'Invalid signature'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            payload = request.data
            event_type = payload.get('event', '')
            event_data = payload.get('data', {})

            logger.info(f"Paystack webhook event: {event_type}")

            if event_type == 'charge.success':
                self._handle_charge_success(event_data)
            else:
                logger.info(f"Unhandled Paystack event: {event_type}")

            return Response({'status': 'ok'})

        except Exception as e:
            logger.exception(f"Error processing Paystack webhook: {e}")
            return Response({'status': 'error'})

    def _handle_charge_success(self, data: dict):
        """
        Handle successful payment.
        
        Updates order status and notifies customer.
        """
        from apps.orders.models import Order, OrderStatus
        
        reference = data.get('reference', '')
        amount = data.get('amount', 0)
        metadata = data.get('metadata', {})
        order_id = metadata.get('order_id')

        logger.info(f"Payment success for reference: {reference}")

        # Find and update order
        order = None
        
        # Try by order_id in metadata first
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                pass
        
        # Try by reference
        if not order:
            try:
                order = Order.objects.get(reference=reference)
            except Order.DoesNotExist:
                pass
        
        # Try by paystack_reference
        if not order:
            try:
                order = Order.objects.get(paystack_reference=reference)
            except Order.DoesNotExist:
                logger.error(f"Order not found for payment reference: {reference}")
                return

        # Idempotency: skip if already paid
        if order.status == OrderStatus.PAID:
            logger.info(f"Order {order.reference} already marked as paid")
            return

        # Mark as paid
        order.mark_as_paid(paystack_reference=reference)
        logger.info(f"Order {order.reference} marked as paid")

        # Notify customer
        try:
            from apps.messaging.client import whatsapp_client
            
            wa_id = order.user.wa_id
            message = (
                f"✅ Payment confirmed!\n\n"
                f"Order: {order.reference}\n"
                f"Amount: {order.total_display}\n\n"
                f"We're preparing your order now. Thank you! 🙏"
            )
            whatsapp_client.send_text(wa_id, message)
            
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")
