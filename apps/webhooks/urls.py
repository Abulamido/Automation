"""
Webhook URL routing.
"""
from django.urls import path
from . import views

urlpatterns = [
    # WhatsApp webhook (verification + messages)
    path('whatsapp/', views.WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
    
    # Paystack webhook (payment confirmations)
    path('paystack/', views.PaystackWebhookView.as_view(), name='paystack_webhook'),
]
