import gc
from urllib import urequest

import jpegdec
import machine
import sdcard
import uos

from inky_app_base import InkyAppBase

FILENAME = "/sd/xkcd-daily.jpg"
ENDPOINT = "https://pimoroni.github.io/feed2image/xkcd-daily.jpg"


class DailyXkcdApp(InkyAppBase):
    def __init__(self, graphics=None, width=None, height=None):
        super().__init__(graphics, width, height)
        self.sd = None
        self.sd_spi = None
        self.img_url = None

    def setup(self):
        # Setup SD card and determine image URL based on display type
        self.sd_spi = machine.SPI(0, sck=machine.Pin(18, machine.Pin.OUT), mosi=machine.Pin(
            19, machine.Pin.OUT), miso=machine.Pin(16, machine.Pin.OUT))
        self.sd = sdcard.SDCard(self.sd_spi, machine.Pin(22))
        try:
            uos.mount(self.sd, "/sd")
        except Exception:
            pass  # Already mounted or error
        gc.collect()
        # Set image URL based on display type
        if self.display_type == "5.7":
            self.img_url = "https://pimoroni.github.io/feed2image/xkcd-daily.jpg"
        elif self.display_type == "4.0":
            self.img_url = "https://pimoroni.github.io/feed2image/xkcd-640x400-daily.jpg"
        elif self.display_type == "7.3":
            self.img_url = "https://pimoroni.github.io/feed2image/xkcd-800x480-daily.jpg"
        else:
            self.img_url = ENDPOINT

    def teardown(self):
        # Optionally unmount SD or cleanup
        self.sd = None
        self.sd_spi = None
        self.img_url = None

    def update(self):
        url = self.img_url or ENDPOINT
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
            print("Error downloading XKCD image:", e)
            self.show_error("Unable to download XKCD image!")

    def draw(self):
        gc.collect()
        jpeg = jpegdec.JPEG(self.graphics)
        self.graphics.set_pen(1)
        self.graphics.clear()
        try:
            jpeg.open_file(FILENAME)
            jpeg.decode()
        except Exception as e:
            print("Error decoding/displaying XKCD image:", e)
            self.show_error("Unable to display XKCD image!")
        self.graphics.update()

    @property
    def UPDATE_INTERVAL(self):
        return 240


# Module-level app instance for compatibility
app = DailyXkcdApp()
