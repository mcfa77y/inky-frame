"""
Weather App refactored to use ELM architecture.

This is the new implementation following Model-View-Update pattern
with lifecycle hooks for better maintainability and testability.
"""

import gc
from urllib import urequest

import jpegdec
import machine
import sdcard
import uos

from core.elm_events import ButtonEvent, NavigationEvent
from core.elm_inky_app_base import ElmInkyAppBase
from models.weather_model import WeatherModel
from utils.Timer import Timer

FILENAME = "/sd/weather-daily.jpg"
FLASK_SERVER_BASE = "https://saved-heron-driving.ngrok-free.app"
DEFAULT_ZIPCODE = "94110"  # San Francisco default


class WeatherAppElm(ElmInkyAppBase):
    """Weather app using ELM architecture."""

    def __init__(self):
        super().__init__()
        self.sd = None
        self.sd_spi = None
        self.flask_base_url = FLASK_SERVER_BASE
        self.update_timer = Timer(duration_seconds=self.update_minute_interval * 60)

        # Setup SD card
        self._setup_sd_card()

    def _setup_sd_card(self):
        """Setup SD card for storing weather images."""
        self.sd_spi = machine.SPI(0, sck=machine.Pin(18, machine.Pin.OUT),
                                   mosi=machine.Pin(19, machine.Pin.OUT),
                                   miso=machine.Pin(16, machine.Pin.OUT))
        self.sd = sdcard.SDCard(self.sd_spi, machine.Pin(22))
        try:
            uos.mount(self.sd, "/sd")
        except Exception as e:
            self.logger.error(f"Unable to mount SD card: {e}")
        gc.collect()

    def init(self) -> WeatherModel:
        """Initialize the initial WeatherModel state."""
        return WeatherModel(
            zipcode=DEFAULT_ZIPCODE,
            current_view_index=0,
            weather_views=["current", "forecast", "today"],
            image_path=FILENAME,
            last_update_time=0,
            is_loading=True  # Start by loading initial weather data
        )

    def on_init(self, model: WeatherModel) -> None:
        """Called after model initialization - trigger initial data download."""
        current_view = model.weather_views[model.current_view_index]
        self._download_weather(model.zipcode, current_view)
        self.update_timer.start()

    def on_exit(self, model: WeatherModel) -> None:
        """Cleanup on app exit."""
        self.sd = None
        self.sd_spi = None

    def _handle_button_event(self, model: WeatherModel, event: ButtonEvent) -> WeatherModel:
        """Handle button press events."""
        if event.button == 'a':
            # Previous view
            new_index = (model.current_view_index - 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index).with_loading(True)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._download_weather(new_model.zipcode, current_view)
            self._reset_timer()
            return new_model
        elif event.button == 'b':
            # Next view
            new_index = (model.current_view_index + 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index).with_loading(True)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._download_weather(new_model.zipcode, current_view)
            self._reset_timer()
            return new_model
        elif event.button == 'c':
            # Refresh current view
            new_model = model.with_loading(True)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._download_weather(new_model.zipcode, current_view)
            self._reset_timer()
            return new_model
        elif event.button == 'e':
            # Home button - return to launcher (handled by main loop)
            return model

        return model

    def _handle_navigation_event(self, model: WeatherModel, event: NavigationEvent) -> WeatherModel:
        """Handle navigation events (next/previous)."""
        if event.direction == 'next':
            new_index = (model.current_view_index + 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index).with_loading(True)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._download_weather(new_model.zipcode, current_view)
            self._reset_timer()
            return new_model
        elif event.direction == 'previous':
            new_index = (model.current_view_index - 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index).with_loading(True)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._download_weather(new_model.zipcode, current_view)
            self._reset_timer()
            return new_model

        return model

    def _handle_refresh_event(self, model: WeatherModel) -> WeatherModel:
        """Handle refresh event."""
        new_model = model.with_loading(True)
        current_view = new_model.weather_views[new_model.current_view_index]
        self._download_weather(new_model.zipcode, current_view)
        self._reset_timer()
        return new_model

    def _handle_timer_event(self, model: WeatherModel) -> WeatherModel:
        """Handle timer event for periodic updates."""
        if self.update_timer.is_expired():
            new_model = model.with_loading(True)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._download_weather(new_model.zipcode, current_view)
            self.update_timer.reset()
            self.update_timer.start()
            return new_model
        return model

    def view(self, model: WeatherModel) -> None:
        """Pure function: render Model to display."""
        self.graphics.set_pen(1)
        self.graphics.clear()

        if model.is_loading:
            self._show_loading_indicator()
        elif model.error_message:
            self.show_error(model.error_message)
        else:
            self._display_weather_image(model.image_path)

        self.graphics.update()

    def _show_loading_indicator(self):
        """Display loading indicator."""
        self.graphics.set_pen(2)
        self.graphics.text("Loading...", 10, self.height // 2, self.width, 3)

    def _display_weather_image(self, image_path: str):
        """Display the weather image from SD card."""
        gc.collect()
        jpeg = jpegdec.JPEG(self.graphics)
        try:
            jpeg.open_file(image_path)
            jpeg.decode()
        except Exception as e:
            self.logger.error(f"Error decoding/displaying weather image: {e}")
            self.show_error("Unable to display weather image!")

    def _download_weather(self, zipcode: str, view_type: str = "current"):
        """Download weather image for specified zipcode and view type."""
        base_url = f"{self.flask_base_url}/weather/apple/{zipcode}"

        if view_type == "current":
            endpoint = f"{base_url}/current"
        elif view_type == "forecast":
            endpoint = f"{base_url}/forecast"
        elif view_type == "today":
            endpoint = f"{base_url}/today"
        else:
            endpoint = base_url

        if self.width and self.height:
            url = f"{endpoint}?width={self.width}&height={self.height}"
        else:
            url = endpoint

        self.logger.info(f"Downloading {view_type} weather for {zipcode} from {url}")
        try:
            socket = urequest.urlopen(url)
            data = bytearray(1024)
            with open(FILENAME, "wb") as f:
                while True:
                    if socket.readinto(data) == 0:
                        break
                    f.write(data)
            socket.close()
            del data
            gc.collect()
        except Exception as e:
            self.logger.error(f"Error downloading weather image: {e}")
            self.show_error("Unable to download weather image!")

    def _reset_timer(self) -> None:
        """Reset the update timer after manual refresh."""
        self.update_timer.reset()
        self.update_timer.start()

    @property
    def update_minute_interval(self) -> int:
        """Return the update interval in minutes."""
        return 30  # Update weather every 30 minutes


# Module-level app instance for compatibility
app = WeatherAppElm()
