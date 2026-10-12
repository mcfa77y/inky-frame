import gc  # type: ignore

import machine  # type: ignore
import sdcard  # type: ignore
import uos  # type: ignore
from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY  # 7.3"
from picographics import PicoGraphics

from .inky_helper import get_inky_frame_type
from .logger import Logger


class InkyAppBase:
    """
    Base class for all Inky Frame apps.
    Provides a standard interface and shared logic for all apps.
    """

    def __init__(self):
        """Initialize and return the graphics object and display dimensions."""
        self.graphics = PicoGraphics(DISPLAY)
        self.width, self.height = self.graphics.get_bounds()
        self.graphics.set_font("bitmap8")
        self.display_type = get_inky_frame_type(self.height) if self.height is not None else None
        self.logger = Logger(default_context={"app": self.__class__.__name__})
        self.sd = None
        self.sd_spi = None

    def setup_sd_card(self):
        """Setup SD card for storing images.

        Initializes SPI and mounts the SD card to /sd.
        Apps that need SD card storage should call this in their __init__.
        """
        self.sd_spi = machine.SPI(
            0,
            sck=machine.Pin(18, machine.Pin.OUT),
            mosi=machine.Pin(19, machine.Pin.OUT),
            miso=machine.Pin(16, machine.Pin.OUT),
        )
        self.sd = sdcard.SDCard(self.sd_spi, machine.Pin(22))
        try:
            uos.mount(self.sd, "/sd")
        except Exception as e:
            self.logger.error(f"Unable to mount SD card: {e}")
        gc.collect()

    def cleanup_sd_card(self):
        """Cleanup SD card resources."""
        self.sd = None
        self.sd_spi = None

    def _cleanup_sd_card(self):
        """Alias for cleanup_sd_card for backwards compatibility."""
        self.cleanup_sd_card()

    def show_error(self, message="Unable to display image!"):
        """
        Draw a standard error message box at the center of the screen.
        Uses self.graphics, self.WIDTH, self.HEIGHT by default, but allows overrides.
        """
        graphics = self.graphics
        width = self.width
        height = self.height

        graphics.set_pen(4)
        graphics.rectangle(0, (height // 2) - 20, width, 40)
        graphics.set_pen(1)
        graphics.text(message, 5, (height // 2) - 15, width, 2)
        # graphics.text("Check your network settings in secrets.py", 5, (height // 2) + 2, width, 2)

    def teardown(self):
        """Perform any cleanup logic when the app is exited/unloaded."""
        raise NotImplementedError("teardown() must be implemented by subclass")

    def update(self):
        """Update app state (to be implemented by subclass)."""
        raise NotImplementedError("update() must be implemented by subclass")

    def draw(self):
        """Draw app content to the display (to be implemented by subclass)."""
        raise NotImplementedError("draw() must be implemented by subclass")

    @property
    def update_minute_interval(self) -> int:
        """Return the update interval in minutes (override in subclass if needed)."""
        return 10

    # Button press handlers (to be implemented by subclass if needed)
    def button_a_press(self):
        """Handle button A press (override in subclass if needed)."""
        pass

    def button_b_press(self):
        """Handle button B press (override in subclass if needed)."""
        pass

    def button_c_press(self):
        """Handle button C press (override in subclass if needed)."""
        pass

    def button_d_press(self):
        """Handle button D press (override in subclass if needed)."""
        pass

    def button_e_press(self):
        """Handle button E press (override in subclass if needed)."""
        pass
