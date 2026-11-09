"""1-bit BMP decoder for Inky Frame framebuffer."""

import struct

BMP_MAGIC = b"BM"


def _draw_bmp_byte_pixels(graphics, byte_val: int, x: int, y: int, width: int, pen_0: int, pen_1: int):
    for bit in range(8):
        px = x + bit
        if px >= width:
            break
        pen = pen_1 if (byte_val & (0x80 >> bit)) else pen_0
        graphics.set_pen(pen)
        graphics.pixel(px, y)


def _draw_bmp_row(graphics, row_buf: bytearray, y: int, width: int, pen_0: int, pen_1: int):
    """Draw a single unpacked row of 1-bit BMP bytes to the framebuffer."""
    x = 0
    for byte_val in row_buf:
        if x >= width:
            break
        if byte_val == 0xFF:
            graphics.set_pen(pen_1)
            graphics.pixel_span(x, y, min(8, width - x))
        elif byte_val == 0x00:
            graphics.set_pen(pen_0)
            graphics.pixel_span(x, y, min(8, width - x))
        else:
            _draw_bmp_byte_pixels(graphics, byte_val, x, y, width, pen_0, pen_1)
        x += 8


def decode_1bit_bmp(graphics, filename: str, logger) -> bool:
    """Decode uncompressed 1-bit BMP directly onto Inky Frame framebuffer."""
    try:
        with open(filename, "rb") as f:
            header = f.read(54)
            if len(header) < 54 or not header.startswith(BMP_MAGIC):
                return False

            offset = struct.unpack("<I", header[10:14])[0]
            width, height, _, bpp, compression = struct.unpack("<iiHHI", header[18:34])

            if bpp != 1 or compression != 0:
                logger.error(f"Unsupported BMP format: bpp={bpp}, comp={compression}")
                return False

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
                if f.readinto(row_buf) < row_bytes:
                    break
                _draw_bmp_row(graphics, row_buf, y, width, pen_0, pen_1)
        return True
    except Exception as e:
        logger.error(f"Error decoding 1-bit BMP: {e}")
        return False
