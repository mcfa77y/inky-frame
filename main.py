import gc
import time

import core.inky_helper as inky_utils
from apps.launcher.launcher_app import app as launcherApp
from core.elm_runtime import ElmRuntime
from core.logger import Logger

main_logger = Logger(default_context={"app": "main"})

def main():
    # A short delay to give USB chance to initialise
    time.sleep(0.5)

    # Turn any LEDs off that may still be on from last run.
    inky_utils.clear_button_leds()
    inky_utils.led_warn.off()

    # Default to Weather app on boot (no state.json dependency)
    from apps.weather.weather_elm import app as weatherApp
    main_logger.info("Defaulting to Weather app on boot")
    
    inky_utils.network_connect()

    # Get some memory back, we really need it!
    gc.collect()

    # Initialize ELM runtime with the weather app and launcher
    runtime = ElmRuntime(weatherApp, launcher_app=launcherApp)
    runtime.start()
    main_logger.info("Starting ELM event-driven mode - Button E returns to launcher")

    # Interactive main loop - check for button presses and handle navigation
    while True:
        # Handle button navigation through the runtime
        runtime.handle_events()
        
        # Small delay to prevent excessive CPU usage
        time.sleep(0.1)


if __name__ == "__main__":
    main()
