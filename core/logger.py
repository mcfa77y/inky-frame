import sys

import machine


class Logger:
    LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

    def __init__(self, default_context=None, min_level="INFO"):
        self.default_context = default_context or {}
        self.min_level = min_level
        self.rtc = machine.RTC()

    def set_min_level(self, level):
        if level in self.LEVELS:
            self.min_level = level

    def _log(self, message, level, context=None):
        if level not in self.LEVELS:
            level = "INFO"
        if self.LEVELS.index(level) < self.LEVELS.index(self.min_level):
            return
        current_time = self.rtc.datetime()
        timestamp = f"{current_time[0]}-{current_time[1]}-{current_time[2]} {current_time[4]}:{current_time[5]}:{current_time[6]}"
        merged_context = self.default_context.copy()
        if context:
            merged_context.update(context)
        context_str = ""
        if merged_context:
            context_str = " | " + "\n".join(f"{k}={v}" for k, v in merged_context.items())
        msg = f"[{timestamp}] [{level}]{context_str}: {message}"
        print(msg, file=sys.stderr if level in ("ERROR", "WARNING") else sys.stdout)

    def debug(self, message, context=None):
        self._log(message, "DEBUG", context)

    def info(self, message, context=None):
        self._log(message, "INFO", context)

    def warning(self, message, context=None):
        self._log(message, "WARNING", context)

    def error(self, message, context=None):
        self._log(message, "ERROR", context)
