import gc
import struct
from urllib import urequest  # type: ignore[attr-defined]

import jpegdec
import pngdec
import urequests

from core.inky_app_base import InkyAppBase

# Try loading TRMNL settings from secrets.py if present
try:
    from secrets import TRMNL_API_KEY  # type: ignore[import-not-found]
except ImportError:
    TRMNL_API_KEY = ""

try:
    from secrets import TRMNL_BASE_URL  # type: ignore[import-not-found]
except ImportError:
    TRMNL_BASE_URL = "http://byos.local"

try:
    from secrets import TRMNL_DEVICE_ID  # type: ignore[import-not-found]
except ImportError:
    TRMNL_DEVICE_ID = ""

IMAGE_FILENAME = "/sd/trmnl-display.img"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8"
BMP_MAGIC = b"BM"
FW_VERSION = "1.8.16"


class TRMNLApp(InkyAppBase):
    """TRMNL Display Client for Inky Frame 7.3 Pico 2.

    Fetches rendered screen content from the TRMNL Display API and renders
    it onto the 800x480 7-colour e-paper display.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        device_id: str | None = None,
    ):
        super().__init__()
        self.api_key = TRMNL_API_KEY if api_key is None else api_key
        raw_base = TRMNL_BASE_URL if base_url is None else base_url
        self.base_url = (raw_base or "http://byos.local").rstrip("/")
        self.device_id = TRMNL_DEVICE_ID if device_id is None else device_id
        self.refresh_rate = 900  # Default 15 min refresh per TRMNL spec
        self.friendly_id = ""
        self.current_filename = ""
        self.has_image = False
        self.setup_message = ""
        self.setup_sd_card()

        if not self.device_id:
            try:
                import network  # type: ignore[import-not-found]

                mac = network.WLAN(network.STA_IF).config("mac")
                self.device_id = ":".join(f"{b:02X}" for b in mac)
            except Exception:
                self.device_id = "00:00:00:00:00:00"

    def teardown(self):
        self.cleanup_sd_card()
        self.has_image = False

    def request_setup(self) -> dict | None:
        """Call /api/setup to pair or provision device on the TRMNL server."""
        url = f"{self.base_url}/api/setup"
        headers = {
            "ID": self.device_id,
            "FW-Version": FW_VERSION,
            "Model": "og",
            "Content-Type": "application/json",
        }
        try:
            self.logger.info(f"Polling TRMNL Setup API: {url}")
            resp = urequests.get(url, headers=headers)
            data = resp.json() if resp.status_code in (200, 202) else None
            resp.close()
            return data
        except Exception as e:
            self.logger.error(f"Failed to query TRMNL Setup API: {e}")
            return None

    def fetch_display_metadata(self, endpoint: str = "/api/display") -> dict | None:
        """Call TRMNL Display API and return response metadata."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "ID": self.device_id,
            "Access-Token": self.api_key,
            "FW-Version": FW_VERSION,
            "Model": "og",
            "Width": str(self.width or 800),
            "Height": str(self.height or 480),
            "Content-Type": "application/json",
        }
        try:
            self.logger.info(f"Polling TRMNL Display API: {url}")
            resp = urequests.get(url, headers=headers)
            if resp.status_code not in (200, 0, 202):
                self.logger.error(f"TRMNL API error HTTP {resp.status_code}: {resp.text}")
                resp.close()
                return None
            data = resp.json()
            resp.close()
            return data
        except Exception as e:
            self.logger.error(f"Failed to query TRMNL Display API: {e}")
            return None

    def download_image(self, image_url: str) -> bool:
        """Download remote image to SD card in chunks to minimize heap usage."""
        try:
            self.logger.info(f"Downloading TRMNL image from {image_url}")
            sock = urequest.urlopen(image_url)
            buf = bytearray(1024)
            with open(IMAGE_FILENAME, "wb") as f:
                while True:
                    n = sock.readinto(buf)
                    if n == 0:
                        break
                    f.write(memoryview(buf)[:n])
            sock.close()
            del buf
            gc.collect()
            return True
        except Exception as e:
            self.logger.error(f"Error downloading TRMNL image: {e}")
            return False

    def decode_1bit_bmp(self, filename: str) -> bool:
        """Decode uncompressed 1-bit BMP directly onto Inky Frame framebuffer."""
        try:
            with open(filename, "rb") as f:
                header = f.read(54)
                if len(header) < 54 or not header.startswith(BMP_MAGIC):
                    return False

                offset = struct.unpack("<I", header[10:14])[0]
                width, height, _, bpp, compression = struct.unpack("<iiHHI", header[18:34])

                if bpp != 1 or compression != 0:
                    self.logger.error(f"Unsupported BMP format: bpp={bpp}, comp={compression}")
                    return False

                # Read 2 palette entries (8 bytes: B, G, R, 0)
                palette_data = f.read(8)
                c0_brightness = palette_data[0] + palette_data[1] + palette_data[2]
                c1_brightness = palette_data[4] + palette_data[5] + palette_data[6]
                pen_0 = 1 if c0_brightness > c1_brightness else 0
                pen_1 = 0 if pen_0 == 1 else 1

                top_down = height < 0
                abs_height = abs(height)
                row_bytes = ((width + 31) // 32) * 4

                f.seek(offset)
                row_buf = bytearray(row_bytes)

                for r in range(abs_height):
                    y = r if top_down else (abs_height - 1 - r)
                    n = f.readinto(row_buf)
                    if n < row_bytes:
                        break

                    x = 0
                    for byte_val in row_buf:
                        if x >= width:
                            break
                        if byte_val == 0xFF:
                            span = min(8, width - x)
                            self.graphics.set_pen(pen_1)
                            self.graphics.pixel_span(x, y, span)
                        elif byte_val == 0x00:
                            span = min(8, width - x)
                            self.graphics.set_pen(pen_0)
                            self.graphics.pixel_span(x, y, span)
                        else:
                            for bit in range(8):
                                px = x + bit
                                if px >= width:
                                    break
                                pen = pen_1 if (byte_val & (0x80 >> bit)) else pen_0
                                self.graphics.set_pen(pen)
                                self.graphics.pixel(px, y)
                        x += 8
            return True
        except Exception as e:
            self.logger.error(f"Error decoding 1-bit BMP: {e}")
            return False

    def draw_setup_screen(self):
        """Render pairing and onboarding instructions when device is unconfigured."""
        g = self.graphics
        w = self.width or 800
        h = self.height or 480

        g.set_pen(1)
        g.clear()

        # Header bar
        g.set_pen(0)
        g.rectangle(0, 0, w, 60)
        g.set_pen(1)
        g.set_font("sans")
        g.text("TRMNL DISPLAY  |  SETUP & PAIRING", 20, 40, scale=1.0)

        # Body info
        g.set_pen(0)
        g.set_font("sans")
        g.text("Register this device on your TRMNL server dashboard:", 30, 110, scale=0.8)

        # Box for device credentials
        g.rectangle(30, 140, w - 60, 150)
        g.set_pen(1)
        g.rectangle(32, 142, w - 64, 146)
        g.set_pen(0)
        g.text(f"Device MAC (ID):  {self.device_id}", 50, 180, scale=0.9)
        g.text(f"Server URL:       {self.base_url}", 50, 220, scale=0.9)
        if self.friendly_id:
            g.text(f"Friendly ID:      {self.friendly_id}", 50, 260, scale=0.9)

        if self.setup_message:
            g.text(self.setup_message, 30, 330, scale=0.7)

        # Footer
        g.set_font("bitmap8")
        g.text("Button A: Refresh / Pair    Button B: Reload Current", 30, h - 30, scale=2)
        self.graphics.update()

    def update(self, advance_playlist: bool = True):
        """Fetch next (or current) screen from TRMNL API or request setup."""
        if not self.api_key:
            setup_data = self.request_setup()
            if setup_data:
                self.api_key = setup_data.get("api_key", "")
                self.friendly_id = setup_data.get("friendly_id", "")
                self.setup_message = setup_data.get("message", "")
                setup_img = setup_data.get("image_url")
                if setup_img:
                    if self.download_image(setup_img):
                        self.has_image = True
                        return

            if not self.api_key:
                self.has_image = False
                return

        endpoint = "/api/display" if advance_playlist else "/api/display/current"
        metadata = self.fetch_display_metadata(endpoint)
        if not metadata:
            self.show_error("Unable to connect to TRMNL API")
            self.graphics.update()
            self.has_image = False
            return

        status = metadata.get("status")
        if status == 202:
            self.setup_message = "Device pending approval on server..."
            setup_img = metadata.get("image_url")
            if setup_img and self.download_image(setup_img):
                self.has_image = True
            else:
                self.has_image = False
            return

        image_url = metadata.get("image_url")
        if not image_url:
            self.show_error("No image returned from TRMNL")
            self.graphics.update()
            self.has_image = False
            return

        filename = metadata.get("filename", "")
        if filename and filename == self.current_filename:
            self.logger.info(f"Image {filename} already cached, skipping download")
            self.has_image = True
        else:
            success = self.download_image(image_url)
            if success:
                self.has_image = True
                if filename:
                    self.current_filename = filename
            else:
                self.show_error("Failed to download TRMNL screen")
                self.graphics.update()
                self.has_image = False

        api_refresh = metadata.get("refresh_rate")
        if isinstance(api_refresh, int) and api_refresh >= 60:
            self.refresh_rate = api_refresh

    def button_a_press(self):
        """Button A: advance to next playlist item."""
        self.logger.info("Button A pressed: advance TRMNL playlist")
        self.update(advance_playlist=True)
        self.draw()

    def button_b_press(self):
        """Button B: refresh current screen without advancing playlist."""
        self.logger.info("Button B pressed: reload current TRMNL screen")
        self.update(advance_playlist=False)
        self.draw()

    def button_c_press(self):
        """Button C: re-check setup and pair."""
        self.logger.info("Button C pressed: retry setup/pair")
        self.api_key = ""
        self.update(advance_playlist=True)
        self.draw()

    def draw(self):
        """Render downloaded TRMNL image or setup screen to Inky Frame display."""
        if not self.has_image:
            self.draw_setup_screen()
            return

        gc.collect()
        self.graphics.set_pen(1)
        self.graphics.clear()

        try:
            with open(IMAGE_FILENAME, "rb") as f:
                header = f.read(8)
        except OSError as e:
            self.logger.error(f"Cannot read image file: {e}")
            self.show_error("Image file missing on SD card")
            self.graphics.update()
            return

        try:
            if header.startswith(PNG_MAGIC):
                png = pngdec.PNG(self.graphics)
                png.open_file(IMAGE_FILENAME)
                png.decode(0, 0)
            elif header.startswith(JPEG_MAGIC):
                jpeg = jpegdec.JPEG(self.graphics)
                jpeg.open_file(IMAGE_FILENAME)
                jpeg.decode()
            elif header.startswith(BMP_MAGIC):
                if not self.decode_1bit_bmp(IMAGE_FILENAME):
                    self.show_error("Failed to decode 1-bit BMP")
                    self.graphics.update()
                    return
            else:
                self.logger.error(f"Unrecognized image header: {header!r}")
                self.show_error("Unsupported image format from TRMNL")
                self.graphics.update()
                return
        except Exception as e:
            self.logger.error(f"Error decoding image: {e}")
            self.show_error("Unable to decode TRMNL image")
            self.graphics.update()
            return

        self.graphics.update()

    def sleep_until_next_refresh(self):
        """Put Inky Frame into deep sleep using RTC alarm."""
        sleep_minutes = max(1, self.refresh_rate // 60)
        self.logger.info(f"Sleeping for {sleep_minutes} minutes")
        try:
            import inky_frame  # type: ignore[import-not-found]

            inky_frame.sleep_for(sleep_minutes)
        except Exception as e:
            self.logger.warning(f"Hardware sleep not available: {e}")

    @property
    def update_interval(self) -> int:
        """Update interval in seconds (clamped to at least 1 minute)."""
        return max(60, self.refresh_rate)


app = TRMNLApp()
