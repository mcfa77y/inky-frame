"""TRMNL image rendering: magic-byte detection and decoder dispatch."""

import jpegdec
import pngdec

from .trmnl_bmp import BMP_MAGIC, decode_1bit_bmp

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8"


def render_image_file(graphics, img_path: str, logger, show_error) -> bool:
    """Detect image format by header bytes and decode onto the framebuffer.

    Returns True when an image was decoded; caller still calls graphics.update().
    On failure this calls show_error(message) and returns False.
    """
    try:
        with open(img_path, "rb") as f:
            header = f.read(8)
    except OSError as e:
        logger.error(f"Cannot read image file: {e}")
        show_error("Image file missing on SD card")
        return False

    try:
        if header.startswith(PNG_MAGIC):
            png = pngdec.PNG(graphics)
            png.open_file(img_path)
            png.decode(0, 0)
        elif header.startswith(JPEG_MAGIC):
            jpeg = jpegdec.JPEG(graphics)
            jpeg.open_file(img_path)
            jpeg.decode()
        elif header.startswith(BMP_MAGIC):
            return decode_1bit_bmp(graphics, img_path, logger)
        else:
            logger.error(f"Unrecognized image header: {header!r}")
            show_error("Unsupported image format from TRMNL")
            return False
    except Exception as e:
        logger.error(f"Error decoding image: {e}")
        show_error("Unable to decode TRMNL image")
        return False

    return True
