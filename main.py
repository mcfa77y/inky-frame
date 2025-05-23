import gc
import time

# Uncomment the line for your Inky Frame display size
from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY  # 7.3"
from picographics import PicoGraphics

import inky_helper as inky_utils
from launcher_app import app as launcherApp
from logger import Logger

main_logger = Logger(default_context={"app": "main"})


def connect_wifi():
    """Attempt to connect to WiFi using secrets.py, if available."""
    try:
        from secrets import WIFI_PASSWORD, WIFI_SSID
        inky_utils.network_connect(WIFI_SSID, WIFI_PASSWORD)
    except ImportError:
        print("Create secrets.py with your WiFi credentials")


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

    inky_utils.clear_button_leds()

    if inky_utils.file_exists("state.json"):
        # Loads the JSON and launches the app
        inky_utils.load_state()
        inky_utils.launch_app(inky_utils.state['run'])
    else:
        # Use the LauncherApp as the app
        inky_utils.app = launcherApp
    main_logger.debug(
        f"{inky_utils.file_exists('state.json')} {inky_utils.state['run']}")
    connect_wifi()

    # Get some memory back, we really need it!
    gc.collect()

    # The main loop executes the update and draw function from the imported app,
    # and then goes to sleep ZzzzZZz
    max_count = 10
    count = 0
    while True:
        inky_utils.app.update()
        inky_utils.app.draw()
        inky_utils.sleep(inky_utils.app.update_interval)
        # main_logger.info(
        #     f"App: {inky_utils.app.__class__.__name__} | Interval: {inky_utils.app.update_interval} | Count: {count}")
        count += 1
        # if count >= max_count:
        #     main_logger.info("Main loop completed")
        #     break


if __name__ == "__main__":
    main()
