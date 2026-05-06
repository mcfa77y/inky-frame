import gc
import time

import inky_frame
import inky_helper as inky_utils
from launcher_app import app as launcherApp
from logger import Logger
from elm_events import ButtonEvent

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
current_model = None

def handle_button_press():
    """Handle button presses using event-driven architecture."""
    global button_states, loading_action, current_model
    
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
            main_logger.info(f"Button {button_name.upper()} pressed")
            
            # Start wave pattern for visual feedback
            inky_utils.start_wave_pattern()
            
            try:
                # Check if it's an ELM app with init/update/view methods
                if hasattr(inky_utils.app, 'init') and hasattr(inky_utils.app, 'update') and hasattr(inky_utils.app, 'view'):
                    # ELM mode: use event-driven architecture
                    if button_name == 'e':
                        # Home button - return to launcher
                        main_logger.info("Home button pressed - returning to launcher")
                        inky_utils.app = launcherApp
                        current_model = inky_utils.app.init()
                        inky_utils.app.on_init(current_model)
                        inky_utils.app.view(current_model)
                    else:
                        # Create ButtonEvent and dispatch
                        event = ButtonEvent(button=button_name)
                        current_model = inky_utils.app.update(current_model, event)
                        inky_utils.app.view(current_model)
                elif hasattr(inky_utils.app, f"button_{button_name}_press"):
                    # Legacy mode: use old button press methods
                    button_method = f"button_{button_name}_press"
                    getattr(inky_utils.app, button_method)()
                    inky_utils.app.draw()
                else:
                    main_logger.debug(f"Button {button_name} pressed but no handler found")
            except Exception as e:
                main_logger.error(f"Error handling button {button_name} press: {e}")
            finally:
                # Stop wave pattern
                inky_utils.stop_wave_pattern()
                loading_action = False
        
        # Update button state
        button_states[button_name] = current_state

def main():
    global current_model
    
    # A short delay to give USB chance to initialise
    time.sleep(0.5)

    # Turn any LEDs off that may still be on from last run.
    inky_utils.clear_button_leds()
    inky_utils.led_warn.off()

    # Default to Weather app on boot (no state.json dependency)
    from weather_elm import app as weatherApp
    inky_utils.app = weatherApp
    main_logger.info("Defaulting to Weather app on boot")
    
    inky_utils.network_connect()

    # Get some memory back, we really need it!
    gc.collect()

    # Initialize app using ELM pattern if available
    if hasattr(inky_utils.app, 'init') and hasattr(inky_utils.app, 'update') and hasattr(inky_utils.app, 'view'):
        # ELM mode
        current_model = inky_utils.app.init()
        inky_utils.app.on_init(current_model)
        inky_utils.app.view(current_model)
        main_logger.info("Starting ELM event-driven mode - Button E returns to launcher")
    else:
        # Legacy mode
        inky_utils.app.update()
        inky_utils.app.draw()
        main_logger.info("Starting legacy mode - Press buttons A-E for app-specific actions")

    # Interactive main loop - check for button presses and handle navigation
    while True:
        # Handle button navigation
        handle_button_press()
        
        # Small delay to prevent excessive CPU usage
        time.sleep(0.1)


if __name__ == "__main__":
    main()
