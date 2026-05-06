import gc
from urllib import urequest

import jpegdec
import machine
import sdcard
import uos
import urandom

from core.inky_app_base import InkyAppBase

FILENAME = "/sd/softer-world-daily.jpg"
# SERVER_BASE_URL = "https://saved-heron-driving.ngrok-free.app"
SERVER_BASE_URL = "http://181.41.202.117:33337"


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
        self.flask_base_url = SERVER_BASE_URL

    def teardown(self):
        # Optionally unmount SD or cleanup
        self.sd = None
        self.sd_spi = None
        self.img_url = None

    def update(self):
        self.download_comic(self.current_comic)

    def download_comic(self, comic_num):
        """Download a specific comic by number"""
        # Generate URL with query parameters for dimensions
        base_url = f"{self.flask_base_url}/comic/{comic_num}"
        
        # Add width and height query parameters using actual display dimensions
        if self.width and self.height:
            url = f"{base_url}?width={self.width}&height={self.height}"
        else:
            # Default: use endpoint without custom dimensions
            url = base_url
        
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
        self.logger.info(f"Downloaded comic {comic_num}")

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

    def random_comic(self):
        """Go to a random comic"""
        self.current_comic = urandom.randint(1, self.max_comic)
        self.logger.info(f"Random comic: {self.current_comic}")
        self.download_comic(self.current_comic)

    # Button press handlers
    def button_a_press(self):
        """Button A: Go to previous comic"""
        self.previous_comic()

    def button_b_press(self):
        """Button B: Go to next comic"""
        self.next_comic()

    def button_c_press(self):
        """Button C: Go to random comic"""
        self.random_comic()

    def button_d_press(self):
        """Button D: Refresh current comic"""
        self.logger.info(f"Refreshing comic {self.current_comic}")
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
