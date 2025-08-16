
import time
from machine import reset
import inky_helper as inky_utils
from inky_app_base import InkyAppBase


def handle_launcher_selection(button, app_name):
    """Helper for handling launcher button selection and state update."""
    button.led_on()
    inky_utils.update_state(app_name)
    time.sleep(0.5)
    reset()


class LauncherApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.logger.debug("LauncherApp.__init__ called")

        self.menu_items = [
            (4, "A. NASA Picture of the Day", 340,
             inky_utils.inky_frame.button_a, "nasa_apod"),
            (6, "B. Word Clock", 280, inky_utils.inky_frame.button_b, "word_clock"),
            (2, "C. Daily XKCD", 220, inky_utils.inky_frame.button_c, "daily_xkcd"),
            (3, "D. Headlines", 160, inky_utils.inky_frame.button_d, "news_headlines"),
            (0, "E. Carbon Intensity", 100,
             inky_utils.inky_frame.button_e, "carbon_intensity"),
        ]
        self.width_offsets = [100, 150, 200, 250, 300]
        self.y_offset = 0
        self.selected_app = None
        self.is_draw_completed = False
        self.logger.debug(
            f"LauncherApp initialized with menu_items: {[item[1] for item in self.menu_items]}")

    def update(self):
        # self.logger.debug("LauncherApp.update called")
        # Wait for user to select an app
        for _, _, _, button, app_name in self.menu_items:
            button_state = button.read()
            # self.logger.debug(
            #     f"Checking button for app '{app_name}': state={button_state}")
            if button_state:
                self.logger.debug(f"Button pressed for app: {app_name}")
                handle_launcher_selection(button, app_name)

    def draw(self):
        if self.is_draw_completed:
            # self.logger.debug("Draw skipped: is_draw_completed is True")
            return
        self.logger.debug("LauncherApp.draw called")
        inky_utils.led_warn.on()
        graphics = self.graphics
        width = self.width
        height = self.height
        y_offset = self.y_offset
        self.logger.debug(
            f"Drawing launcher screen: width={width}, height={height}, y_offset={y_offset}")
        graphics.set_pen(1)
        graphics.clear()
        graphics.set_font("bitmap8")
        graphics.set_pen(0)
        graphics.set_pen(graphics.create_pen(255, 215, 0))
        graphics.rectangle(0, 0, width, 50)
        graphics.set_pen(0)
        title = "Launcher"
        title_len = graphics.measure_text(title, 4) // 2
        graphics.text(title, (width // 2 - title_len), 10, width, 4)
        for idx, (pen, text, y_base, button, app_name) in enumerate(self.menu_items):
            self.logger.debug(
                f"Drawing menu item: {text} at y_base={y_base}, pen={pen}")
            graphics.set_pen(pen)
            graphics.rectangle(30, height - (y_base + y_offset),
                               width - self.width_offsets[idx], 50)
            graphics.set_pen(1)
            graphics.text(text, 35, height - (y_base - 15 + y_offset), 600, 3)
        graphics.set_pen(graphics.create_pen(220, 220, 220))
        for idx, (_, _, y_base, _, _) in enumerate(self.menu_items):
            graphics.rectangle(
                width - self.width_offsets[idx], height - (y_base + y_offset), 70 + idx * 50, 50)
        graphics.set_pen(0)
        note = "Hold A + E, then press Reset, to return to the Launcher"
        note_len = graphics.measure_text(note, 2) // 2
        graphics.text(note, (width // 2 - note_len), height - 30, 600, 2)
        graphics.update()
        inky_utils.led_warn.off()
        self.is_draw_completed = True
        self.logger.debug(
            "LauncherApp.draw completed and is_draw_completed set to True")
        inky_utils.led_warn.off()
        return

    @property
    def update_interval(self):
        return 0


# Module-level app instance for compatibility
app = LauncherApp()
