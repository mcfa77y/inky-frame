import sys
import time


class Logger:
    LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

    def __init__(self, default_context=None):
        self.default_context = default_context or {}

    def _log(self, message, level, context=None):
        if level not in self.LEVELS:
            level = "INFO"
        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S") if hasattr(time, "strftime") else str(time.time())
        merged_context = self.default_context.copy()
        if context:
            merged_context.update(context)
        context_str = ""
        if merged_context:
            context_str = " | " + \
                " ".join(f"{k}={v}" for k, v in merged_context.items())
        msg = f"[{timestamp}] [{level}]{context_str}: {message}"
        print(msg, file=sys.stderr if level in (
            "ERROR", "WARNING") else sys.stdout)

    def debug(self, message, context=None):
        self._log(message, "DEBUG", context)

    def info(self, message, context=None):
        self._log(message, "INFO", context)

    def warning(self, message, context=None):
        self._log(message, "WARNING", context)

    def error(self, message, context=None):
        self._log(message, "ERROR", context)
