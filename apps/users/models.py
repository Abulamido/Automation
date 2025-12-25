"""
User Profile model for WhatsApp users.

WhatsApp users don't authenticate traditionally - they're identified by their
WhatsApp ID (wa_id), which is typically their phone number in international format.
This model stores the identity and any additional info collected during conversation.
"""
from django.db import models


class UserProfile(models.Model):
    """
    Represents a WhatsApp user interacting with the ordering system.
    
    The wa_id is the canonical identifier from WhatsApp's Cloud API and serves
    as our primary lookup key. Phone number is stored separately for display
    and payment purposes (Paystack requires phone/email).
    
    Attributes:
        wa_id: WhatsApp identifier (usually phone in E.164 format)
        phone_number: Display-friendly phone number
        name: User's name (collected during conversation or from WhatsApp profile)
        email: Email address (required for Paystack, collected during checkout)
        default_address: Previously saved delivery address for convenience
    """
    wa_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="WhatsApp ID from Meta API (usually phone number)"
    )
    phone_number = models.CharField(
        max_length=20,
        help_text="Phone number for display and payment purposes"
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's name from WhatsApp profile or conversation"
    )
    email = models.EmailField(
        blank=True,
        help_text="Email for Paystack transactions"
    )
    default_address = models.TextField(
        blank=True,
        help_text="Saved delivery address for quick checkout"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.phone_number})"

    @classmethod
    def get_or_create_from_whatsapp(cls, wa_id: str, phone_number: str = None, 
                                     name: str = None) -> 'UserProfile':
        """
        Get existing user or create new one from WhatsApp message data.
        
        This is the primary entry point for user lookup/creation when
        processing incoming WhatsApp messages.
        
        Args:
            wa_id: WhatsApp ID from the message
            phone_number: Phone number (often same as wa_id)
            name: Profile name from WhatsApp if available
            
        Returns:
            UserProfile instance (existing or newly created)
        """
        user, created = cls.objects.get_or_create(
            wa_id=wa_id,
            defaults={
                'phone_number': phone_number or wa_id,
                'name': name or '',
            }
        )
        
        # Update name if we now have it and didn't before
        if not created and name and not user.name:
            user.name = name
            user.save(update_fields=['name', 'updated_at'])
            
        return user
