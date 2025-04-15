from inky_helper import get_inky_frame_type


class InkyAppBase:
    """
    Base class for all Inky Frame apps.
    Provides a standard interface and shared logic for all apps.
    """

    def show_error(self, message="Unable to display image!", graphics=None, width=None, height=None):
        """
        Draw a standard error message box at the center of the screen.
        Uses self.graphics, self.WIDTH, self.HEIGHT by default, but allows overrides.
        """
        g = graphics if graphics is not None else self.graphics
        w = width if width is not None else self.WIDTH
        h = height if height is not None else self.HEIGHT
        if g is None or w is None or h is None:
            return
        g.set_pen(4)
        g.rectangle(0, (h // 2) - 20, w, 40)
        g.set_pen(1)
        g.text(message, 5, (h // 2) - 15, w, 2)
        g.text("Check your network settings in secrets.py", 5, (h // 2) + 2, w, 2)

    def __init__(self, graphics=None, width=None, height=None):
        self.graphics = graphics
        self.WIDTH = width
        self.HEIGHT = height
        self.display_type = get_inky_frame_type(
            height) if height is not None else None

    def setup(self):
        """Perform any initialization logic when the app is loaded/launched."""
        raise NotImplementedError("setup() must be implemented by subclass")

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
    def UPDATE_INTERVAL(self):
        """Return the update interval in minutes (override in subclass if needed)."""
        return 10
