"""
ELM Runtime for Inky Frame Apps.

Encapsulates the event loop, button handling, and event dispatching
for ELM-architected applications. This is the platform/runtime layer
that bridges hardware events to the app's update/view cycle.
"""

import inky_frame

from core.elm_events import ButtonEvent
from core.inky_helper import start_wave_pattern, stop_wave_pattern
from core.logger import Logger


class ElmRuntime:
    """Runtime for ELM-architected Inky Frame apps."""

    def __init__(self, app, launcher_app=None):
        """Initialize the runtime with an app and optional launcher."""
        self.app = app
        self.launcher_app = launcher_app
        self.logger = Logger(default_context={"app": "ElmRuntime"})
        
        # Button state tracking
        self.button_states = {
            'a': False,
            'b': False,
            'c': False,
            'd': False,
            'e': False
        }
        
        # Button hardware mapping
        self.buttons = {
            'a': inky_frame.button_a,
            'b': inky_frame.button_b,
            'c': inky_frame.button_c,
            'd': inky_frame.button_d,
            'e': inky_frame.button_e
        }
        
        # Runtime state
        self.loading_action = False
        self.current_model = None
        
        # Detect if app is ELM-based
        self.is_elm_app = (
            hasattr(app, 'init') and 
            hasattr(app, 'update') and 
            hasattr(app, 'view')
        )
        
        self.logger.info(f"Runtime initialized. ELM mode: {self.is_elm_app}")

    def start(self):
        """Start the runtime and initialize the app."""
        if self.is_elm_app:
            self.current_model = self.app.init()
            self.app.on_init(self.current_model)
            self.app.view(self.current_model)
            self.logger.info("ELM app started")
        else:
            # Legacy mode
            self.app.update()
            self.app.draw()
            self.logger.info("Legacy app started")

    def handle_events(self):
        """Process button events and dispatch to app."""
        if self.loading_action:
            return
        
        for button_name, button_obj in self.buttons.items():
            current_state = button_obj.read()
            last_state = self.button_states[button_name]
            
            # Detect button press (transition from False to True)
            if current_state and not last_state:
                self._handle_button_press(button_name)
                # Break to process one button press event per frame
                self.button_states[button_name] = current_state
                break
            
            # Update button state
            self.button_states[button_name] = current_state

        # Check timers if in ELM mode and not loading
        if self.is_elm_app and not self.loading_action:
            try:
                timer_event = self.app.on_timer(self.current_model)
                if timer_event:
                    self.logger.info("Timer event triggered")
                    self.loading_action = True
                    start_wave_pattern()
                    try:
                        self.current_model = self.app.update(self.current_model, timer_event)
                        self.app.view(self.current_model)
                    finally:
                        stop_wave_pattern()
                        self.loading_action = False
            except Exception as e:
                self.logger.error(f"Error handling timer event: {e}")

    def _handle_button_press(self, button_name: str):
        """Handle a single button press event."""
        self.loading_action = True
        self.logger.info(f"Button {button_name.upper()} pressed")
        
        # Start wave pattern for visual feedback
        start_wave_pattern()
        
        try:
            if self.is_elm_app:
                self._dispatch_elm_event(button_name)
            else:
                self._dispatch_legacy_event(button_name)
        except Exception as e:
            self.logger.error(f"Error handling button {button_name} press: {e}")
        finally:
            stop_wave_pattern()
            self.loading_action = False

    def _dispatch_elm_event(self, button_name: str):
        """Dispatch button event to ELM app."""
        if button_name == 'e' and self.launcher_app:
            # Home button - return to launcher
            self.logger.info("Home button pressed - returning to launcher")
            self.switch_app(self.launcher_app)
        else:
            # Create ButtonEvent and dispatch
            event = ButtonEvent(button=button_name)
            self.current_model = self.app.update(self.current_model, event)
            self.app.view(self.current_model)

    def _dispatch_legacy_event(self, button_name: str):
        """Dispatch button event to legacy app."""
        button_method = f"button_{button_name}_press"
        if hasattr(self.app, button_method):
            getattr(self.app, button_method)()
            self.app.draw()
        else:
            self.logger.debug(f"Button {button_name} pressed but no handler found")

    def switch_app(self, new_app):
        """Switch to a different app."""
        self.app = new_app
        self.is_elm_app = (
            hasattr(new_app, 'init') and 
            hasattr(new_app, 'update') and 
            hasattr(new_app, 'view')
        )
        self.start()
