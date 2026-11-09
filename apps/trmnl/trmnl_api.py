import gc
from urllib import urequest  # type: ignore[attr-defined]

import urequests

from core.logger import Logger

FW_VERSION = "1.8.16"


class TRMNLApi:
    """Client for TRMNL BYOS/BYOD-S Display and Setup APIs."""

    def __init__(
        self,
        base_url: str = "http://byos.local",
        device_id: str = "00:00:00:00:00:00",
        api_key: str = "",
        fw_version: str = FW_VERSION,
        width: int = 800,
        height: int = 480,
        logger: Logger | None = None,
    ):
        self.base_url = (base_url or "http://byos.local").rstrip("/")
        self.host = self.base_url.split("://", 1)[-1].split("/", 1)[0]
        self.device_id = device_id
        self.api_key = api_key
        self.fw_version = fw_version
        self.width = width
        self.height = height
        self.logger = logger or Logger(default_context={"app": "TRMNLApi"})

    def request_setup(self) -> dict | None:
        """Call /api/setup to pair or provision device on the TRMNL server."""
        url = f"{self.base_url}/api/setup"
        headers = {
            "Host": self.host,
            "ID": self.device_id,
            "FW-Version": self.fw_version,
            "Model": "inky_frame_7_3",
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
            "Host": self.host,
            "ID": self.device_id,
            "Access-Token": self.api_key,
            "FW-Version": self.fw_version,
            "Model": "inky_frame_7_3",
            "Width": str(self.width),
            "Height": str(self.height),
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

    def normalize_image_url(self, image_url: str) -> str:
        """Ensure image URL includes scheme, host, and port matching base_url if omitted."""
        if image_url.startswith("/"):
            return f"{self.base_url}{image_url}"
        base_proto, _, base_host = self.base_url.partition("://")
        if ":" in base_host:
            host_only = base_host.split(":", 1)[0]
            prefix = f"{base_proto}://{host_only}/"
            if image_url.startswith(prefix):
                return f"{self.base_url}/" + image_url[len(prefix) :]
        return image_url

    def download_image(self, image_url: str, target_path: str) -> bool:
        """Download remote image to target path in chunks to minimize heap usage."""
        image_url = self.normalize_image_url(image_url)
        try:
            self.logger.info(f"Downloading TRMNL image from {image_url}")
            sock = urequest.urlopen(image_url)
            buf = bytearray(1024)
            with open(target_path, "wb") as f:
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
