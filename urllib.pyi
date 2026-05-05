# Type stub for urllib module with MicroPython's urequest
# This helps IDEs and type checkers understand the mocked urequest module

from typing import Any, Optional, Dict

class urequest:
    @staticmethod
    def urlopen(
        url: str, 
        data: Optional[bytes] = None, 
        method: str = "GET", 
        headers: Optional[Dict[str, str]] = None,
        stream: Optional[Any] = None
    ) -> Any: ...
