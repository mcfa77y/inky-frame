import gc
from urllib import urequest

import jpegdec
import machine
import sdcard
import uos

from core.inky_app_base import InkyAppBase

FILENAME = "/sd/weather-daily.jpg"
FLASK_SERVER_BASE = "https://saved-heron-driving.ngrok-free.app"
DEFAULT_ZIPCODE = "94102"  # San Francisco default


class WeatherApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.sd = None
        self.sd_spi = None
        self.img_url = None
        self.zipcode = DEFAULT_ZIPCODE
        self.weather_views = ["current", "forecast", "today"]
        self.current_view_index = 0  # Start with current weather

        # Setup SD card and determine image URL based on display type
        self.sd_spi = machine.SPI(0, sck=machine.Pin(18, machine.Pin.OUT), mosi=machine.Pin(
            19, machine.Pin.OUT), miso=machine.Pin(16, machine.Pin.OUT))
        self.sd = sdcard.SDCard(self.sd_spi, machine.Pin(22))
        try:
            uos.mount(self.sd, "/sd")
        except Exception as e:
            self.logger.error(f"Unable to mount SD card: {e}")
            pass  # Already mounted or error
        gc.collect()
        # Set base URL for Flask server - we'll add weather endpoints in update()
        self.flask_base_url = FLASK_SERVER_BASE

    def teardown(self):
        # Optionally unmount SD or cleanup
        self.sd = None
        self.sd_spi = None
        self.img_url = None

    def update(self):
        current_view = self.weather_views[self.current_view_index]
        self.download_weather(self.zipcode, current_view)

    def download_weather(self, zipcode, view_type="current"):
        """Download weather image for specified zipcode and view type"""
        # Generate URL for weather endpoint with display-specific dimensions
        base_url = f"{self.flask_base_url}/weather/apple/{zipcode}"
        
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
            self.show_error("Unable to download weather image!")

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
