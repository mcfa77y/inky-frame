import gc
import time

import inky_frame
import inky_helper as inky_utils
from launcher_app import app as launcherApp
from logger import Logger

main_logger = Logger(default_context={"app": "main"})

# Button state tracking
button_a_last_state = False
button_e_last_state = False
loading_comic = False

def handle_comic_navigation():
    """Handle comic navigation with wave pattern during loading"""
    global button_a_last_state, button_e_last_state, loading_comic
    
    # Check button A (previous comic)
    button_a_current = inky_frame.button_a.read()
    if button_a_current and not button_a_last_state and hasattr(inky_utils.app, 'previous_comic') and not loading_comic:
        loading_comic = True
        main_logger.info("Loading previous comic...")
        
        # Start wave pattern
        inky_utils.start_wave_pattern()
        
        try:
            # Load previous comic
            inky_utils.app.previous_comic()
            # Draw the new comic
            inky_utils.app.draw()
        except Exception as e:
            main_logger.error(f"Error loading previous comic: {e}")
        finally:
            # Stop wave pattern
            inky_utils.stop_wave_pattern()
            loading_comic = False
    
    button_a_last_state = button_a_current
    
    # Check button E (next comic)
    button_e_current = inky_frame.button_e.read()
    if button_e_current and not button_e_last_state and hasattr(inky_utils.app, 'next_comic') and not loading_comic:
        loading_comic = True
        main_logger.info("Loading next comic...")
        
        # Start wave pattern
        inky_utils.start_wave_pattern()
        
        try:
            # Load next comic
            inky_utils.app.next_comic()
            # Draw the new comic
            inky_utils.app.draw()
        except Exception as e:
            main_logger.error(f"Error loading next comic: {e}")
        finally:
            # Stop wave pattern
            inky_utils.stop_wave_pattern()
            loading_comic = False
    
    button_e_last_state = button_e_current

def main():
    # A short delay to give USB chance to initialise
    time.sleep(0.5)

    # Turn any LEDs off that may still be on from last run.
    inky_utils.clear_button_leds()
    inky_utils.led_warn.off()

    if inky_utils.file_exists("state.json"):
        # Loads the JSON and launches the app
        inky_utils.load_state()
        inky_utils.launch_app(inky_utils.state['run'])
    else:
        # Use the LauncherApp as the app
        inky_utils.app = launcherApp
    main_logger.debug(
        f"{inky_utils.file_exists('state.json')} {inky_utils.state['run']}")
    inky_utils.network_connect()

    # Get some memory back, we really need it!
    gc.collect()

    # Initial display
    inky_utils.app.update()
    inky_utils.app.draw()

    # Interactive main loop - check for button presses and handle navigation
    main_logger.info("Starting interactive mode - Press Button A for previous comic, Button E for next comic")
    
    while True:
        # Handle button navigation
        handle_comic_navigation()
        
        # Small delay to prevent excessive CPU usage
        time.sleep(0.1)


if __name__ == "__main__":
    main()
