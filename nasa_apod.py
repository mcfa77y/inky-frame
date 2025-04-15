import gc
from urllib import urequest

import jpegdec
from ujson import load

from inky_app_base import InkyAppBase

gc.collect()

FILENAME = "nasa-apod-daily"
API_URL = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"


class NasaApodApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.apod_title = "Space!"
        self.jpeg = jpegdec.JPEG(self.graphics) if self.graphics else None
        # Set image URL based on display_type from base class
        if self.display_type == "5.7":
            self.img_url = "https://pimoroni.github.io/feed2image/nasa-apod-daily.jpg"
        elif self.display_type == "4.0":
            self.img_url = "https://pimoroni.github.io/feed2image/nasa-apod-640x400-daily.jpg"
        elif self.display_type == "7.3":
            self.img_url = "https://pimoroni.github.io/feed2image/nasa-apod-800x480-daily.jpg"
        else:
            self.img_url = None

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
        except OSError as e:
            print(e)
            self.show_error("Unable to display image!")

        graphics.set_pen(0)
        graphics.rectangle(0, self.height - 25, self.width, 25)
        graphics.set_pen(1)
        graphics.text(self.apod_title, 5, self.height - 20, self.width, 2)

        gc.collect()

        graphics.update()

    @property
    def update_interval(self):
        return 240


# Module-level app instance for compatibility
app = NasaApodApp()
