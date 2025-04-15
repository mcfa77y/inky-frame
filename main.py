import gc
import time

from machine import reset
# Uncomment the line for your Inky Frame display size
# from picographics import PicoGraphics, DISPLAY_INKY_FRAME_4 as DISPLAY  # 4.0"
# from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY      # 5.7"
from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY  # 7.3"
from picographics import PicoGraphics

import inky_helper as inky_utils
from inky_app_base import InkyAppBase


def connect_wifi():
    """Attempt to connect to WiFi using secrets.py, if available."""
    try:
        from secrets import WIFI_PASSWORD, WIFI_SSID
        inky_utils.network_connect(WIFI_SSID, WIFI_PASSWORD)
    except ImportError:
        print("Create secrets.py with your WiFi credentials")


def handle_launcher_selection(button, app_name):
    """Helper for handling launcher button selection and state update."""
    button.led_on()
    inky_utils.update_state(app_name)
    time.sleep(0.5)
    reset()


class LauncherApp(InkyAppBase):
    def __init__(self):
        super().__init__()
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

    def update(self):
        # Wait for user to select an app
        for _, _, _, button, app_name in self.menu_items:
            if button.read():
                handle_launcher_selection(button, app_name)

    def draw(self):
        g = self.graphics
        width = self.width
        height = self.height
        y_offset = self.y_offset
        g.set_pen(1)
        g.clear()
        g.set_font("bitmap8")
        g.set_pen(0)
        g.set_pen(g.create_pen(255, 215, 0))
        g.rectangle(0, 0, width, 50)
        g.set_pen(0)
        title = "Launcher"
        title_len = g.measure_text(title, 4) // 2
        g.text(title, (width // 2 - title_len), 10, width, 4)
        for idx, (pen, text, y_base, button, app_name) in enumerate(self.menu_items):
            g.set_pen(pen)
            g.rectangle(30, height - (y_base + y_offset),
                        width - self.width_offsets[idx], 50)
            g.set_pen(1)
            g.text(text, 35, height - (y_base - 15 + y_offset), 600, 3)
        g.set_pen(g.create_pen(220, 220, 220))
        for idx, (_, _, y_base, _, _) in enumerate(self.menu_items):
            g.rectangle(
                width - self.width_offsets[idx], height - (y_base + y_offset), 70 + idx * 50, 50)
        g.set_pen(0)
        note = "Hold A + E, then press Reset, to return to the Launcher"
        note_len = g.measure_text(note, 2) // 2
        g.text(note, (width // 2 - note_len), height - 30, 600, 2)
        inky_utils.led_warn.on()
        g.update()
        inky_utils.led_warn.off()


# Module-level app instance for compatibility
launcherApp = LauncherApp()


def main():
    # A short delay to give USB chance to initialise
    time.sleep(0.5)

    # Turn any LEDs off that may still be on from last run.
    inky_utils.clear_button_leds()
    inky_utils.led_warn.off()

    # Launcher shortcut
    if inky_utils.inky_frame.button_a.read() and inky_utils.inky_frame.button_e.read():
        # Use the LauncherApp as the app
        inky_utils.app = launcherApp
        launcherApp.draw()
        while True:
            launcherApp.update()
            launcherApp.draw()

    inky_utils.clear_button_leds()

    if inky_utils.file_exists("state.json"):
        # Loads the JSON and launches the app
        inky_utils.load_state()
        inky_utils.launch_app(inky_utils.state['run'])
    else:
        # Use the LauncherApp as the app
        inky_utils.app = launcherApp
        launcherApp.draw()
        while True:
            launcherApp.update()
            launcherApp.draw()

    connect_wifi()

    # Get some memory back, we really need it!
    gc.collect()

    # The main loop executes the update and draw function from the imported app,
    # and then goes to sleep ZzzzZZz
    while True:
        inky_utils.app.update()
        inky_utils.led_warn.on()
        inky_utils.app.draw()
        inky_utils.led_warn.off()
        inky_utils.sleep(inky_utils.app.update_interval)


if __name__ == "__main__":
    main()
