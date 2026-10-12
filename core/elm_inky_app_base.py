"""
ELM Architecture Base Class for Inky Frame Apps.

Provides a Model-View-Update architecture with lifecycle hooks for
building predictable, testable Inky Frame applications.

Note: MicroPython doesn't support abc methods. They are documented in docstrings for clarity and compatibility with CircuitPython.
"""

from .elm_events import ButtonEvent
from .inky_app_base import InkyAppBase


class ElmInkyAppBase(InkyAppBase):
    """Base class for ELM-architected Inky Frame apps with lifecycle hooks."""

    def __init__(self):
        """Initialize the graphics object and display dimensions."""
        super().__init__()

    def init(self):
        """Initialize the initial Model state.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement init()")

    def update(self, model=None, event=None):
        """Pure function: return new Model based on current Model and Event.

        Default implementation dispatches to specific handler methods based on event type.
        Override for custom event handling logic.
        """
        if event is None:
            return model

        # Map event types to handler method names
        event_handlers = {
            "ButtonEvent": "on_button",
            "TimerEvent": "on_timer",
            "NetworkEvent": "on_network_response",
            "HomeEvent": "on_home",
            "RefreshEvent": "on_refresh",
            "NavigationEvent": "on_navigation",
        }

        event_type = event.__class__.__name__
        handler_name = event_handlers.get(event_type)

        self.logger.debug(f"Event: {event_type}")
        self.logger.debug(f"Handler: {handler_name}")
        if handler_name and hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            return handler(model, event)

        # If no specific handler, return model unchanged
        return model

    def view(self, model) -> None:
        """Pure function: render Model to display (no side effects).

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement view()")

    # Lifecycle hooks (optio)
    def on_init(self, model) -> None:
        """Called after model initialization. Override for setup logic (e.g., network requests)."""
        pass

    def on_exit(self, model) -> None:
        """Called before app exits. Override for cleanup logic (e.g., unmount SD card)."""
        pass

    def on_frame(self, _model):
        """Called every frame before event processing. Return an Event to inject, or None."""
        return None

    def on_button_press(self, _model, _event: ButtonEvent):
        """Called when a button is pressed. Return an Event to process, or None to ignore."""
        return None

    def on_timer(self, _model):
        """Called on timer tick. Return an Event to process, or None."""
        return None

    def on_network_response(self, _data: dict, _model):
        """Called when network data arrives. Return an Event to process, or None."""
        return None
