"""
ConversationSession model for tracking user conversation state.

This is the core of the FSM - each user has a session that tracks their
current state, temporary context data, and active cart.
"""
from django.db import models
from .states import ConversationState


class ConversationSession(models.Model):
    """
    Tracks conversation state for each WhatsApp user.
    
    This model is the heart of the FSM (Finite State Machine) - it persists
    the current state and any temporary data needed across message exchanges.
    
    Key design decisions:
    - One session per user (OneToOne relationship)
    - Context JSON field for flexible temporary data storage
    - last_message_id for idempotency (reject duplicate message processing)
    
    Attributes:
        user: The WhatsApp user this session belongs to
        current_state: Current FSM state (from ConversationState enum)
        context: JSON field for temporary data (selected category, pending item, etc.)
        current_order: Active cart/order in DRAFT status
        last_message_id: Last processed message ID (for idempotency)
    """
    user = models.OneToOneField(
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name='session'
    )
    current_state = models.CharField(
        max_length=50,
        default=ConversationState.START.value,
        help_text="Current conversation state"
    )
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Temporary context data for current state"
    )
    current_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversation_session',
        help_text="Active cart/order"
    )
    last_message_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Last processed message ID for idempotency"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conversation Session'
        verbose_name_plural = 'Conversation Sessions'

    def __str__(self):
        return f"Session for {self.user} - State: {self.current_state}"

    @property
    def state(self) -> ConversationState:
        """Get current state as enum."""
        return ConversationState.from_string(self.current_state)

    @state.setter
    def state(self, value: ConversationState):
        """Set state from enum."""
        self.current_state = value.value

    def transition_to(self, new_state: ConversationState, context_updates: dict = None):
        """
        Transition to a new state with optional context updates.
        
        This is the primary method for state changes - ensures proper
        state persistence and context management.
        
        Args:
            new_state: The target state
            context_updates: Optional dict to merge into context
        """
        self.current_state = new_state.value
        
        if context_updates:
            self.context.update(context_updates)
            
        self.save(update_fields=['current_state', 'context', 'updated_at'])

    def clear_context(self, keys: list = None):
        """
        Clear context data.
        
        Args:
            keys: Optional list of specific keys to clear. If None, clears all.
        """
        if keys:
            for key in keys:
                self.context.pop(key, None)
        else:
            self.context = {}
        self.save(update_fields=['context', 'updated_at'])

    def get_context(self, key: str, default=None):
        """Get a value from context with optional default."""
        return self.context.get(key, default)

    def set_context(self, key: str, value):
        """Set a single context value."""
        self.context[key] = value
        self.save(update_fields=['context', 'updated_at'])

    def is_duplicate_message(self, message_id: str) -> bool:
        """
        Check if this message has already been processed.
        
        Used for idempotency - WhatsApp may deliver the same message
        multiple times.
        
        Args:
            message_id: WhatsApp message ID
            
        Returns:
            True if this message was already processed
        """
        if self.last_message_id == message_id:
            return True
        return False

    def mark_message_processed(self, message_id: str):
        """Record that a message has been processed."""
        self.last_message_id = message_id
        self.save(update_fields=['last_message_id', 'updated_at'])

    @classmethod
    def get_or_create_for_user(cls, user) -> 'ConversationSession':
        """
        Get existing session or create new one for a user.
        
        Args:
            user: UserProfile instance
            
        Returns:
            ConversationSession for the user
        """
        session, created = cls.objects.get_or_create(
            user=user,
            defaults={'current_state': ConversationState.START.value}
        )
        return session

    def reset(self):
        """Reset session to initial state (e.g., on 'restart' command)."""
        self.current_state = ConversationState.START.value
        self.context = {}
        self.save(update_fields=['current_state', 'context', 'updated_at'])
