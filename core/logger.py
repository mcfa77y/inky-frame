import sys

import machine


class _MicroChalk:
    """MicroPython-safe zero-dependency fallback for simple-chalk ANSI styling."""

    def __init__(self, codes=()):
        self._codes = codes

    def _add(self, code):
        return _MicroChalk(self._codes + (code,))

    @property
    def red(self):
        return self._add("31")

    @property
    def green(self):
        return self._add("32")

    @property
    def yellow(self):
        return self._add("33")

    @property
    def cyan(self):
        return self._add("36")

    @property
    def bold(self):
        return self._add("1")

    @property
    def dim(self):
        return self._add("2")

    def __call__(self, text):
        return f"\x1b[{';'.join(self._codes)}m{text}\x1b[0m" if self._codes else str(text)


try:
    from simple_chalk import chalk  # type: ignore[import-untyped]
except (ImportError, AttributeError):
    chalk = _MicroChalk()

LEVEL_STYLES = {
    "DEBUG": chalk.cyan.dim,
    "INFO": chalk.green,
    "WARNING": chalk.yellow,
    "ERROR": chalk.red.bold,
}


class Logger:
    LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

    def __init__(self, default_context=None, min_level="INFO", use_color=True):
        self.default_context = default_context or {}
        self.min_level = min_level
        self.use_color = use_color
        self.rtc = machine.RTC()

    def set_use_color(self, enabled: bool):
        self.use_color = bool(enabled)

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
        level_tag = f"[{level}]"
        if self.use_color and level in LEVEL_STYLES:
            level_tag = LEVEL_STYLES[level](level_tag)
        msg = f"[{timestamp}] {level_tag}{context_str}: {message}"
        print(msg, file=sys.stderr if level in ("ERROR", "WARNING") else sys.stdout)

    def debug(self, message, context=None):
        self._log(message, "DEBUG", context)

    def info(self, message, context=None):
        self._log(message, "INFO", context)

    def warning(self, message, context=None):
        self._log(message, "WARNING", context)

    def error(self, message, context=None):
        self._log(message, "ERROR", context)
