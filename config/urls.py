"""
URL configuration for WhatsApp Orders project.

Routes are minimal - primarily webhook endpoints for external services.
Admin interface is available for menu and order management.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin for menu/order management
    path('admin/', admin.site.urls),
    
    # Webhook endpoints (WhatsApp + Paystack)
    path('webhooks/', include('apps.webhooks.urls')),
]
