import gc
import time

import inky_frame
import inky_helper as inky_utils
from launcher_app import app as launcherApp
from logger import Logger

main_logger = Logger(default_context={"app": "main"})

# Button state tracking
button_states = {
    'a': False,
    'b': False,
    'c': False,
    'd': False,
    'e': False
}
loading_action = False

def handle_button_press():
    """Handle button presses using standardized button press methods"""
    global button_states, loading_action
    
    # Define button mappings
    buttons = {
        'a': inky_frame.button_a,
        'b': inky_frame.button_b,
        'c': inky_frame.button_c,
        'd': inky_frame.button_d,
        'e': inky_frame.button_e
    }
    
    # Check each button for press events
    for button_name, button_obj in buttons.items():
        current_state = button_obj.read()
        last_state = button_states[button_name]
        
        # Detect button press (transition from False to True)
        if current_state and not last_state and not loading_action:
            loading_action = True
            button_method = f"button_{button_name}_press"
            
            # Check if the app has the button press method
            if hasattr(inky_utils.app, button_method):
                main_logger.info(f"Button {button_name.upper()} pressed")
                
                # Start wave pattern for visual feedback
                inky_utils.start_wave_pattern()
                
                try:
                    # Call the button press method
                    getattr(inky_utils.app, button_method)()
                    # Redraw the display
                    inky_utils.app.draw()
                except Exception as e:
                    main_logger.error(f"Error handling button {button_name} press: {e}")
                finally:
                    # Stop wave pattern
                    inky_utils.stop_wave_pattern()
                    loading_action = False
            else:
                loading_action = False
                main_logger.debug(f"Button {button_name} pressed but no handler found")
        
        # Update button state
        button_states[button_name] = current_state

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
    main_logger.info("Starting interactive mode - Press buttons A-E for app-specific actions")
    
    while True:
        # Handle button navigation
        handle_button_press()
        
        # Small delay to prevent excessive CPU usage
        time.sleep(0.1)


if __name__ == "__main__":
    main()
