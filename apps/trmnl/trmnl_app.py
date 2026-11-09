import gc

from core.inky_app_base import InkyAppBase

from .trmnl_api import FW_VERSION, TRMNLApi
from .trmnl_renderer import render_image_file
from .trmnl_view import render_setup_screen

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


def resolve_image_filename() -> str:
    """Return /sd/trmnl-display.img if SD is mounted, else fallback to flash."""
    try:
        import uos  # type: ignore[import-not-found]

        uos.stat("/sd")
        return "/sd/trmnl-display.img"
    except (OSError, AttributeError, ImportError):
        return "/trmnl-display.img"


def _resolve_device_mac() -> str:
    """Read the hardware Wi-Fi MAC address, or return a zero MAC."""
    try:
        import network  # type: ignore[import-not-found]

        mac = network.WLAN(network.STA_IF).config("mac")
        return ":".join(f"{b:02X}" for b in mac)
    except Exception:
        return "00:00:00:00:00:00"


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
        raw_base = TRMNL_BASE_URL if base_url is None else base_url
        self.base_url = (raw_base or "http://byos.local").rstrip("/")
        self.device_id = (TRMNL_DEVICE_ID if device_id is None else device_id) or _resolve_device_mac()
        self.refresh_rate = 900  # Default 15 min refresh per TRMNL spec
        self.friendly_id = ""
        self.current_filename = ""
        self.has_image = False
        self.setup_message = ""
        self.setup_sd_card()

        self.api = TRMNLApi(
            base_url=self.base_url,
            device_id=self.device_id,
            api_key=TRMNL_API_KEY if api_key is None else api_key,
            fw_version=FW_VERSION,
            width=self.width or 800,
            height=self.height or 480,
            logger=self.logger,
        )

    @property
    def api_key(self) -> str:
        return self.api.api_key

    @api_key.setter
    def api_key(self, value: str):
        self.api.api_key = value

    def teardown(self):
        self.cleanup_sd_card()
        self.has_image = False

    def _handle_setup_provisioning(self) -> bool:
        """Attempt auto-provisioning via /api/setup if API key is not configured."""
        if self.api_key:
            return True

        setup_data = self.api.request_setup()
        if setup_data:
            self.api_key = setup_data.get("api_key", "")
            self.friendly_id = setup_data.get("friendly_id", "")
            self.setup_message = setup_data.get("message", "")
            setup_img = setup_data.get("image_url")
            if setup_img and self.api.download_image(setup_img, resolve_image_filename()):
                self.has_image = True
                return False

        self.has_image = False
        return bool(self.api_key)

    def _handle_display_image(self, metadata: dict) -> bool:
        """Download or reuse cached screen image from TRMNL metadata."""
        image_url = metadata.get("image_url")
        if not image_url:
            self.show_error("No image returned from TRMNL")
            self.graphics.update()
            self.has_image = False
            return False

        filename = metadata.get("filename", "")
        if filename and filename == self.current_filename:
            self.logger.info(f"Image {filename} already cached, skipping download")
            self.has_image = True
            return True

        if self.api.download_image(image_url, resolve_image_filename()):
            self.has_image = True
            if filename:
                self.current_filename = filename
            return True

        self.show_error("Failed to download TRMNL screen")
        self.graphics.update()
        self.has_image = False
        return False

    def update(self, advance_playlist: bool = True):
        """Fetch next (or current) screen from TRMNL API or request setup."""
        if not self._handle_setup_provisioning():
            return

        endpoint = "/api/display" if advance_playlist else "/api/display/current"
        metadata = self.api.fetch_display_metadata(endpoint)
        if not metadata:
            self.show_error("Unable to connect to TRMNL API")
            self.graphics.update()
            self.has_image = False
            return

        if metadata.get("status") == 202:
            self.setup_message = "Device pending approval on server..."
            setup_img = metadata.get("image_url")
            self.has_image = bool(setup_img and self.api.download_image(setup_img, resolve_image_filename()))
            return

        self._handle_display_image(metadata)

        api_refresh = metadata.get("refresh_rate")
        if isinstance(api_refresh, int) and api_refresh >= 60:
            self.refresh_rate = api_refresh

    def button_a_press(self):
        """Button A: advance to next playlist item."""
        self.logger.info("Button A pressed: advance TRMNL playlist")
        self.update(advance_playlist=True)

    def button_b_press(self):
        """Button B: refresh current screen without advancing playlist."""
        self.logger.info("Button B pressed: reload current TRMNL screen")
        self.update(advance_playlist=False)

    def button_c_press(self):
        """Button C: re-check setup and pair."""
        self.logger.info("Button C pressed: retry setup/pair")
        self.api_key = ""
        self.update(advance_playlist=True)

    def draw(self):
        """Render downloaded TRMNL image or setup screen to Inky Frame display."""
        if not self.has_image:
            render_setup_screen(
                self.graphics,
                self.width or 800,
                self.height or 480,
                self.device_id,
                self.base_url,
                self.friendly_id,
                self.setup_message,
            )
            return

        gc.collect()
        self.graphics.set_pen(1)
        self.graphics.clear()

        render_image_file(self.graphics, resolve_image_filename(), self.logger, self.show_error)
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
