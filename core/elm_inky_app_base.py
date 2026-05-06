"""
ELM Architecture Base Class for Inky Frame Apps.

Provides a Model-View-Update architecture with lifecycle hooks for
building predictable, testable Inky Frame applications.

Note: MicroPython doesn't support abc methods. They are documented in docstrings for clarity and compatibility with CircuitPython.
"""


import gc  # type: ignore
from typing import Any, Optional

import machine  # type: ignore
import sdcard  # type: ignore
import uos  # type: ignore
from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY  # type: ignore
from picographics import PicoGraphics  # type: ignore

from .inky_helper import get_inky_frame_type
from .logger import Logger


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
        self.sd = None
        self.sd_spi = None

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

    def setup_sd_card(self):
        """Setup SD card for storing images.
        
        Initializes SPI and mounts the SD card to /sd.
        Apps that need SD card storage should call this in their __init__.
        """
        self.sd_spi = machine.SPI(0, sck=machine.Pin(18, machine.Pin.OUT),
                                   mosi=machine.Pin(19, machine.Pin.OUT),
                                   miso=machine.Pin(16, machine.Pin.OUT))
        self.sd = sdcard.SDCard(self.sd_spi, machine.Pin(22))
        try:
            uos.mount(self.sd, "/sd")
        except Exception as e:
            self.logger.error(f"Unable to mount SD card: {e}")
        gc.collect()

    def _cleanup_sd_card(self):
        """Cleanup SD card resources.
        
        Should be called in on_exit() for apps that use SD card.
        """
        self.sd = None
        self.sd_spi = None

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
