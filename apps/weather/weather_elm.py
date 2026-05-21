"""
Weather App refactored to use ELM architecture.

This is the new implementation following Model-View-Update pattern
with lifecycle hooks for better maintainability and testability.
"""

import gc
from urllib import urequest

import jpegdec
import network

from core.elm_events import ButtonEvent, NavigationEvent
from core.elm_inky_app_base import ElmInkyAppBase
from core.inky_helper import network_connect
from models.weather_model import WeatherModel
from utils.Timer import Timer

FILENAME = "/sd/weather-daily.jpg"
API_SERVER_BASE_URL = "https://princess-donut.com"
DEFAULT_ZIPCODE = "94110"  # San Francisco default


class WeatherAppElm(ElmInkyAppBase):
    """Weather app using ELM architecture."""

    def __init__(self):
        super().__init__()
        self.flask_base_url = API_SERVER_BASE_URL
        self.update_timer = Timer(duration_seconds=self.update_minute_interval * 60)

        # Setup SD card
        self.setup_sd_card()

    def init(self) -> WeatherModel:
        """Initialize the initial WeatherModel state."""
        return WeatherModel(
            zipcode=DEFAULT_ZIPCODE,
            current_view_index=0,
            weather_views=["current", "forecast", "today"],
            image_path=FILENAME,
            last_update_time=0,
            is_loading=True,  # Start by loading initial weather data
        )

    def on_init(self, model: WeatherModel) -> None:
        """Called after model initialization - trigger initial data download."""
        current_view = model.weather_views[model.current_view_index]
        success = self._download_weather(model.zipcode, current_view)
        if success:
            model.is_loading = False
            model.error_message = ""
        else:
            model.is_loading = False
            model.error_message = "Unable to download weather image!"
        self.update_timer.start()

    def on_exit(self, model: WeatherModel) -> None:
        """Cleanup on app exit."""
        self._cleanup_sd_card()

    def _update_weather_and_model(
        self, model: WeatherModel, zipcode: str, view_type: str
    ) -> WeatherModel:
        """Download weather image and return the updated model state."""
        success = self._download_weather(zipcode, view_type)
        if success:
            return model.with_loading(False).with_error("")
        else:
            return model.with_error("Unable to download weather image!")

    def _handle_button_event(
        self, model: WeatherModel, event: ButtonEvent
    ) -> WeatherModel:
        """Handle button press events."""
        if event.button == "a":
            # Previous view
            new_index = (model.current_view_index - 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._reset_timer()
            return self._update_weather_and_model(
                new_model, new_model.zipcode, current_view
            )
        elif event.button == "b":
            # Next view
            new_index = (model.current_view_index + 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._reset_timer()
            return self._update_weather_and_model(
                new_model, new_model.zipcode, current_view
            )
        elif event.button == "c":
            # Refresh current view
            current_view = model.weather_views[model.current_view_index]
            self._reset_timer()
            return self._update_weather_and_model(model, model.zipcode, current_view)
        elif event.button == "e":
            # Home button - return to launcher (handled by main loop)
            return model

        return model

    def _handle_navigation_event(
        self, model: WeatherModel, event: NavigationEvent
    ) -> WeatherModel:
        """Handle navigation events (next/previous)."""
        if event.direction == "next":
            new_index = (model.current_view_index + 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._reset_timer()
            return self._update_weather_and_model(
                new_model, new_model.zipcode, current_view
            )
        elif event.direction == "previous":
            new_index = (model.current_view_index - 1) % len(model.weather_views)
            new_model = model.with_view_index(new_index)
            current_view = new_model.weather_views[new_model.current_view_index]
            self._reset_timer()
            return self._update_weather_and_model(
                new_model, new_model.zipcode, current_view
            )

        return model

    def _handle_refresh_event(self, model: WeatherModel) -> WeatherModel:
        """Handle refresh event."""
        current_view = model.weather_views[model.current_view_index]
        self._reset_timer()
        return self._update_weather_and_model(model, model.zipcode, current_view)

    def _handle_timer_event(self, model: WeatherModel) -> WeatherModel:
        """Handle timer event for periodic updates."""
        if self.update_timer.is_expired():
            current_view = model.weather_views[model.current_view_index]
            self.update_timer.reset()
            self.update_timer.start()
            return self._update_weather_and_model(model, model.zipcode, current_view)
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
        base_url = f"{self.flask_base_url}/weather/image?zip={zipcode}"

        if view_type == "current":
            endpoint = f"{base_url}&view=current"
        elif view_type == "forecast":
            endpoint = f"{base_url}&view=forecast"
        elif view_type == "today":
            endpoint = f"{base_url}&view=today"
        else:
            endpoint = base_url

        if self.width and self.height:
            url = f"{endpoint}&width={self.width}&height={self.height}"
        else:
            url = endpoint

        self.logger.info(f"Downloading {view_type} weather for {zipcode} from {url}")
        try:
            # Ensure network is connected before downloading
            wlan = network.WLAN(network.STA_IF)
            if not wlan.isconnected():
                self.logger.warning("WiFi disconnected. Attempting to reconnect...")
                if not network_connect():
                    self.logger.error("WLAN is not connected. Aborting download.")
                    return False

            self.logger.debug(f"Opening URL: {url}")
            socket = urequest.urlopen(url)
            self.logger.debug("Socket opened successfully")
            data = bytearray(1024)

            self.logger.debug(f"Opening file for writing: {FILENAME}")
            with open(FILENAME, "wb") as f:
                chunks = 0
                while True:
                    if socket.readinto(data) == 0:
                        break
                    f.write(data)
                    chunks += 1
                    if chunks % 10 == 0:
                        self.logger.debug(f"Wrote {chunks} chunks...")

            self.logger.debug(f"Download complete. Total chunks: {chunks}")
            socket.close()
            del data
            gc.collect()
            self.logger.debug("Cleanup complete")
            return True
        except Exception as e:
            self.logger.error(f"Error downloading weather image: {e}")
            return False

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
