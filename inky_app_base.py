from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY  # 7.3"
from picographics import PicoGraphics

from inky_helper import get_inky_frame_type
from logger import Logger


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
        self.display_type = get_inky_frame_type(
            self.height) if self.height is not None else None
        self.logger = Logger(default_context={"app": self.__class__.__name__})

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
