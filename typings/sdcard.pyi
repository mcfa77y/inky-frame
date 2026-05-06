"""
SD Card driver for MicroPython.

This module provides support for SD cards via SPI.
"""

from typing import Any
from machine import SPI, Pin

class SDCard:
    """
    SD card driver over SPI.
    
    Example usage::
    
        import machine
        import sdcard
        import uos
        
        spi = machine.SPI(1, sck=machine.Pin(18), mosi=machine.Pin(19), miso=machine.Pin(16))
        sd = sdcard.SDCard(spi, machine.Pin(22))
        uos.mount(sd, '/sd')
    """
    
    def __init__(self, spi: SPI, cs: Pin) -> None:
        """
        Initialize the SD card.
        
        Args:
            spi: The SPI bus to use for communication
            cs: The chip select pin
        """
        ...
    
    def readblocks(self, block_num: int, buf: Any) -> None:
        """Read one or more blocks from the card."""
        ...
    
    def writeblocks(self, block_num: int, buf: Any) -> None:
        """Write one or more blocks to the card."""
        ...
    
    def ioctl(self, cmd: int, arg: int) -> Any:
        """Control the card."""
        ...
