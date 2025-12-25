"""
Base handler class and result type for FSM handlers.

All state handlers inherit from BaseHandler and return HandlerResult.
This ensures consistent interface across all states.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from apps.conversations.states import ConversationState


@dataclass
class HandlerResult:
    """
    Result returned by state handlers.
    
    Contains everything needed to complete the state transition:
    - Response messages to send to user
    - Next state to transition to
    - Context updates to persist
    
    Attributes:
        messages: List of text messages to send (in order)
        next_state: State to transition to
        context_updates: Dict of context key/values to persist
    """
    messages: List[str] = field(default_factory=list)
    next_state: Optional[ConversationState] = None
    context_updates: dict = field(default_factory=dict)

    def add_message(self, message: str):
        """Add a message to the response."""
        self.messages.append(message)


class BaseHandler(ABC):
    """
    Abstract base class for state handlers.
    
    Each state in the FSM has a corresponding handler that processes
    user input and determines the response + next state.
    
    Subclasses must implement:
    - handle(): Process message and return HandlerResult
    
    Optional overrides:
    - get_intro_message(): Message to show when entering this state
    """
    
    # Global keywords that can be used from any state
    GLOBAL_KEYWORDS = {
        'restart': 'restart',
        'menu': 'menu',
        'cart': 'cart',
        'help': 'help',
        'cancel': 'cancel',
    }

    def __init__(self, session):
        """
        Initialize handler with session.
        
        Args:
            session: ConversationSession instance
        """
        self.session = session
        self.user = session.user

    @abstractmethod
    def handle(self, message: str) -> HandlerResult:
        """
        Process user message and return result.
        
        Args:
            message: Normalized user message text
            
        Returns:
            HandlerResult with messages, next state, and context updates
        """
        pass

    def get_intro_message(self) -> Optional[str]:
        """
        Optional message to show when entering this state.
        
        Override in subclasses to provide state-specific intro.
        
        Returns:
            Intro message string, or None
        """
        return None

    def get_help_message(self) -> str:
        """Return help text for this state."""
        return "Type 'menu' to see categories, 'cart' to view your cart, or 'restart' to start over."

    def normalize_input(self, message: str) -> str:
        """Normalize user input for consistent processing."""
        return message.strip().lower()

    def parse_numeric_choice(self, message: str, max_value: int) -> Optional[int]:
        """
        Parse user input as a numeric menu choice.
        
        Args:
            message: User message
            max_value: Maximum valid choice number
            
        Returns:
            Valid choice number (1-indexed), or None if invalid
        """
        try:
            choice = int(message.strip())
            if 1 <= choice <= max_value:
                return choice
        except ValueError:
            pass
        return None

    def check_global_keyword(self, message: str) -> Optional[HandlerResult]:
        """
        Check if message matches a global keyword.
        
        Global keywords allow navigation from any state.
        
        Args:
            message: Normalized message
            
        Returns:
            HandlerResult if keyword matched, None otherwise
        """
        normalized = self.normalize_input(message)
        
        if normalized in ('restart', 'start over', 'begin'):
            self.session.reset()
            return HandlerResult(
                messages=["Session restarted! Let's begin again."],
                next_state=ConversationState.START
            )
            
        if normalized == 'help':
            return HandlerResult(
                messages=[self.get_help_message()],
                next_state=self.session.state  # Stay in current state
            )
            
        return None
