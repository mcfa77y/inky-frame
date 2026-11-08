import gc
from urllib import urequest

import jpegdec

from core.inky_app_base import InkyAppBase
from utils.constants import API_SERVER_BASE_URL

FILENAME = "/sd/weather-daily.jpg"
DEFAULT_ZIPCODE = "94102"  # San Francisco default


class WeatherApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.img_url = None
        self.zipcode = DEFAULT_ZIPCODE
        self.weather_views = ["current", "forecast", "today"]
        self.current_view_index = 0  # Start with current weather
        self.setup_sd_card()
        # Set base URL for Flask server - we'll add weather endpoints in update()
        self.flask_base_url = API_SERVER_BASE_URL

    def teardown(self):
        # Optionally unmount SD or cleanup
        self.cleanup_sd_card()
        self.img_url = None

    def update(self):
        current_view = self.weather_views[self.current_view_index]
        self.download_weather(self.zipcode, current_view)

    def download_weather(self, zipcode, view_type="current"):
        """Download weather image for specified zipcode and view type"""
        # Generate URL for weather endpoint with display-specific dimensions
        base_url = f"{self.flask_base_url.rstrip('/')}/weather/apple/{zipcode}"

        if view_type == "current":
            endpoint = f"{base_url}/current"
        elif view_type == "forecast":
            endpoint = f"{base_url}/forecast"
        elif view_type == "today":
            endpoint = f"{base_url}/today"
        else:
            # Default to general weather endpoint
            endpoint = f"{base_url}"

        # Add width and height query parameters using actual display dimensions
        if self.width and self.height:
            url = f"{endpoint}?width={self.width}&height={self.height}"
        else:
            # Default: use endpoint without custom dimensions
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
            self.show_error("03 Unable to download weather image!")

    def next_weather_view(self):
        """Go to the next weather view"""
        self.current_view_index = (self.current_view_index + 1) % len(self.weather_views)
        current_view = self.weather_views[self.current_view_index]
        self.logger.info(f"Next weather view: {current_view}")
        self.download_weather(self.zipcode, current_view)

    def previous_weather_view(self):
        """Go to the previous weather view"""
        self.current_view_index = (self.current_view_index - 1) % len(self.weather_views)
        current_view = self.weather_views[self.current_view_index]
        self.logger.info(f"Previous weather view: {current_view}")
        self.download_weather(self.zipcode, current_view)

    # Button press handlers
    def button_a_press(self):
        """Button A: Go to previous weather view"""
        self.previous_weather_view()

    def button_b_press(self):
        """Button B: Go to next weather view"""
        self.next_weather_view()

    def button_c_press(self):
        """Button C: Refresh current weather view"""
        current_view = self.weather_views[self.current_view_index]
        self.logger.info(f"Refreshing {current_view} weather view")
        self.download_weather(self.zipcode, current_view)

    def draw(self):
        gc.collect()
        jpeg = jpegdec.JPEG(self.graphics)
        self.graphics.set_pen(1)
        self.graphics.clear()
        try:
            jpeg.open_file(FILENAME)
            jpeg.decode()
        except Exception as e:
            self.logger.error(f"Error decoding/displaying weather image: {e}")
            self.show_error("Unable to display weather image!")
        self.graphics.update()

    @property
    def update_minute_interval(self) -> int:
        return 30  # Update weather every 30 minutes


# Module-level app instance for compatibility
app = WeatherApp()
