"""
ELM Architecture Base Class for Inky Frame Apps.

Provides a Model-View-Update architecture with lifecycle hooks for
building predictable, testable Inky Frame applications.

Note: MicroPython doesn't support abc ethodsare
documented in docstrings rrthtrataaffenforccdcwith deciratorsd ciratorsdecorators.
"""

from typing import Any, Optional
from tytyng import Any, Optional
from piping import Any, Optional
from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY
from picographics import PicoGraphics

from inky_helper import get_inky_frame_type
from logger import Logger


class ElmInkyAppBase:
    """Base class for ELM-architected Inky Frame apps with lifecycle hooks."""

    def __init__(self):
        """Initialize the graphics object and display dimensions."""
        self.graphics = PicoGraphics(DISPLAY)
        self.width, self.height = self.graphics.get_bounds()
        self.graphics.set_font("bitmap8")
        self.display_type = get_inky_frame_type(
            self.height) if self.height is not None else None
        self.logger = Logger(default_context={"app": self.__class__.__name__})

    def init(self):
        """Initialize the initial Model state.
        
        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement init()")

    def update(self, model, event):
        """Pure function: return new Model based on current Model and Event.
        
        Default implementation dispatches to specific handler methods based on event type.
        Override for custom event handling logic.
        """
        # Try to dispatch to handler method based on event type
        event_type_name = event.__class__.__name__
        handler_name = f"_handle_{event_type_name.lower()}_event"
        
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            return handler(model, event)
        
        # If no specific handler, return model unchanged
        return model

    def view(self, model: Any) -> None:
        """Pure function: render Model to display (no side effects).
        
        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement view()")

    # Lifecycle hooks (optio)
    def on_init(self, model: Any) -> None:
        """Called after model initialization. Override for setup logic (e.g., network requests)."""
        pass

    def on_exit(self, model: Any) -> None:
        """Called before app exits. Override for cleanup logic (e.g., unmount SD card)."""
        pass

    def on_frame(self, model: Any) -> Optional[Any]:
        """Called every frame before event processing. Return an Event to inject, or None."""
        return None

    def on_button_press(self, button: str, model: Any) -> Optional[Any]:
        """Called when a button is pressed. Return an Event to process, or None to ignore."""
        return None

    def on_timer(self, model: Any) -> Optional[Any]:
        """Called on timer tick. Return an Event to process, or None."""
        return None

    def on_network_response(self, data: dict, model: Any) -> Optional[Any]:
        """Called when network data arrives. Return an Event to process, or None."""
        return None

    def show_error(self, message="Unable to display image!"):
        """
        Draw a standard error message box at the center of the screen.
        Uses self.graphics, self.width, self.height by default.
        """
        graphics = self.graphics
        width = self.width
        height = self.height

        graphics.set_pen(4)
        graphics.rectangle(0, (height // 2) - 20, width, 40)
        graphics.set_pen(1)
        graphics.text(message, 5, (height // 2) - 15, width, 2)

    @property
    def update_minute_interval(self) -> int:
        """Return the update interval in minutes (override in subclass if needed)."""
        return 10
