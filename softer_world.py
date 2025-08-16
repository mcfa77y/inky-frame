import gc
import urandom
from urllib import urequest

import jpegdec
import machine
import sdcard
import uos

from inky_app_base import InkyAppBase

FILENAME = "/sd/softer-world-daily.jpg"
FLASK_SERVER_BASE = "https://saved-heron-driving.ngrok-free.app"


class DailySofterWorldApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.sd = None
        self.sd_spi = None
        self.img_url = None
        self.current_comic = urandom.randint(1, 1248)  # Start with random comic
        self.max_comic = 1248  # Softer World had comics 1-1248

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
        # Set base URL for Flask server - we'll add comic number and dimensions in update()
        self.flask_base_url = FLASK_SERVER_BASE

    def teardown(self):
        # Optionally unmount SD or cleanup
        self.sd = None
        self.sd_spi = None
        self.img_url = None

    def update(self):
        self.download_comic(self.current_comic)

    def download_comic(self, comic_num):
        """Download a specific comic by number"""
        # Generate URL based on display type with proper Flask server endpoint format
        if self.display_type == "5.7":
            # Use specific comic with 600x448 dimensions for 5.7" display
            url = f"{self.flask_base_url}/comic/{comic_num}/600x448"
        elif self.display_type == "4.0":
            # Use specific comic with 640x400 dimensions for 4.0" display
            url = f"{self.flask_base_url}/comic/{comic_num}/640x400"
        elif self.display_type == "7.3":
            # Use specific comic with 800x480 dimensions for 7.3" display
            url = f"{self.flask_base_url}/comic/{comic_num}/800x480"
        else:
            # Default: just get the comic without custom dimensions
            url = f"{self.flask_base_url}/comic/{comic_num}"
        
        self.logger.info(f"Downloading comic {comic_num} from {url}")
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
            self.logger.error(f"Error downloading Softer World image: {e}")
            self.show_error("Unable to download Softer World image!")

    def next_comic(self):
        """Go to the next comic"""
        if self.current_comic < self.max_comic:
            self.current_comic += 1
        else:
            self.current_comic = 1  # Wrap around to first comic
        self.logger.info(f"Next comic: {self.current_comic}")
        self.download_comic(self.current_comic)

    def previous_comic(self):
        """Go to the previous comic"""
        if self.current_comic > 1:
            self.current_comic -= 1
        else:
            self.current_comic = self.max_comic  # Wrap around to last comic
        self.logger.info(f"Previous comic: {self.current_comic}")
        self.download_comic(self.current_comic)

    def draw(self):
        gc.collect()
        jpeg = jpegdec.JPEG(self.graphics)
        self.graphics.set_pen(1)
        self.graphics.clear()
        try:
            jpeg.open_file(FILENAME)
            jpeg.decode()
        except Exception as e:
            self.logger.error(f"Error decoding/displaying Softer World image: {e}")
            self.show_error("Unable to display Softer World image!")
        self.graphics.update()

    @property
    def update_minute_interval(self) -> int:
        return 240


# Module-level app instance for compatibility
app = DailySofterWorldApp()
