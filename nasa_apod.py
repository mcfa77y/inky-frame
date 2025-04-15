import gc
from urllib import urequest

import jpegdec
from ujson import load

from inky_app_base import InkyAppBase

gc.collect()

FILENAME = "nasa-apod-daily"
API_URL = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"


class NasaApodApp(InkyAppBase):
    def __init__(self, graphics=None, width=None, height=None):
        super().__init__(graphics, width, height)
        self.apod_title = None
        self.jpeg = jpegdec.JPEG(graphics) if graphics else None
        # Set image URL based on display_type from base class
        if self.display_type == "5.7":
            self.img_url = "https://pimoroni.github.io/feed2image/nasa-apod-daily.jpg"
        elif self.display_type == "4.0":
            self.img_url = "https://pimoroni.github.io/feed2image/nasa-apod-640x400-daily.jpg"
        elif self.display_type == "7.3":
            self.img_url = "https://pimoroni.github.io/feed2image/nasa-apod-800x480-daily.jpg"
        else:
            self.img_url = None

    def setup(self):
        # Fetch APOD title from API
        try:
            # Grab the image
            socket = urequest.urlopen(self.img_url)

            gc.collect()

            data = bytearray(1024)
            with open(FILENAME, "wb") as f:
                while True:
                    if socket.readinto(data) == 0:
                        break
                    f.write(data)
            socket.close()
            del data
            gc.collect()
        except OSError as e:
            print(e)
            self.show_error("Unable to download image")

    def teardown(self):
        # Clear loaded data/resources
        self.apod_title = None
        self.img_url = None
        # Optionally, reset jpeg decoder or other resources


    def update(self):
        # This could be used for periodic refreshes if needed
        pass

    def draw(self):
        graphics = self.graphics
        jpeg = jpegdec.JPEG(graphics)
        gc.collect()  # For good measure...

        graphics.set_pen(1)
        graphics.clear()

        try:
            jpeg.open_file(FILENAME)
            jpeg.decode()
        except OSError:
            self.show_error()

        graphics.set_pen(0)
        graphics.rectangle(0, HEIGHT - 25, WIDTH, 25)
        graphics.set_pen(1)
        graphics.text(self.apod_title, 5, HEIGHT - 20, WIDTH, 2)

        gc.collect()

        graphics.update()

    @property
    def UPDATE_INTERVAL(self):
        return 240


# Provide a module-level app instance for compatibility
app = NasaApodApp()
