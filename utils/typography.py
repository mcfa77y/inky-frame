import gc
from urllib import urequest

import jpegdec
import machine
import sdcard
import uos

from core.inky_app_base import InkyAppBase

FILENAME = "/sd/typography-sheet.jpg"
FLASK_SERVER_BASE = "https://saved-heron-driving.ngrok-free.app"


class TypographyApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.sd = None
        self.sd_spi = None
        self.img_url = None

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
        self.download_image()

    def download_image(self):
        """Download weather image for specified zipcode and view type"""
        # Generate URL for weather endpoint with display-specific dimensions
        endpoint = f"{self.flask_base_url}/typography/sheet"
        
        
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
