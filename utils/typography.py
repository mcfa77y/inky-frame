import gc
from urllib import urequest

import jpegdec

from core.inky_app_base import InkyAppBase

from .constants import API_SERVER_BASE_URL

FILENAME = "/sd/typography-sheet.jpg"
FLASK_SERVER_BASE = API_SERVER_BASE_URL


class TypographyApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.img_url = None
        self.setup_sd_card()
        # Set base URL for Flask server - we'll add weather endpoints in update()
        self.flask_base_url = FLASK_SERVER_BASE

    def teardown(self):
        # Optionally unmount SD or cleanup
        self.cleanup_sd_card()
        self.img_url = None

    def update(self):
        self.download_image()

    def download_image(self):
        """Download weather image for specified zipcode and view type"""
        # Generate URL for weather endpoint with display-specific dimensions
        endpoint = f"{self.flask_base_url.rstrip('/')}/typography/sheet"

        # Add width and height query parameters using actual display dimensions
        if self.width and self.height:
            url = f"{endpoint}?width={self.width}&height={self.height}"
        else:
            # Default: use endpoint without custom dimensions
            url = endpoint

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
            self.logger.error(f"Error downloading typography sheet: {e}")
            self.show_error("Unable to download typography sheet!")

    def button_c_press(self):
        """Button C: Refresh current weather view"""
        self.logger.info("Refreshing typography sheet")
        self.download_image()

    def draw(self):
        gc.collect()
        jpeg = jpegdec.JPEG(self.graphics)
        self.graphics.set_pen(1)
        self.graphics.clear()
        try:
            jpeg.open_file(FILENAME)
            jpeg.decode()
        except Exception as e:
            self.logger.error(f"Error decoding/displaying typography sheet: {e}")
            self.show_error("Unable to display typography sheet!")
        self.graphics.update()

    @property
    def update_minute_interval(self) -> int:
        return 30  # Update typography sheet every 30 minutes


# Module-level app instance for compatibility
app = TypographyApp()
