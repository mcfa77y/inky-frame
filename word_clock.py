import machine
import ntptime

from inky_app_base import InkyAppBase


def approx_time(hours, minutes):
    nums = {0: "twelve", 1: "one", 2: "two",
            3: "three", 4: "four", 5: "five", 6: "six",
            7: "seven", 8: "eight", 9: "nine", 10: "ten",
            11: "eleven", 12: "twelve"}
    if hours == 12:
        hours = 0
    if minutes > 0 and minutes < 8:
        return "it is about " + nums[hours] + " O'Clock"
    elif minutes >= 8 and minutes < 23:
        return "it is about quarter past " + nums[hours]
    elif minutes >= 23 and minutes < 38:
        return "it is about half past " + nums[hours]
    elif minutes >= 38 and minutes < 53:
        return "it is about quarter to " + nums[hours + 1]
    else:
        return "it is about " + nums[hours + 1] + " O'Clock"


class WordClockApp(InkyAppBase):
    def __init__(self, graphics=None, width=None, height=None):
        super().__init__(graphics, width, height)
        self.rtc = machine.RTC()
        self.time_string = None
        self.words = ["it", "d", "is", "m", "about", "l", "half", "c", "quarter", "b", "to", "u", "past", "n", "one",
                      "two", "three", "four", "five", "six", "eleven", "ten", "nine", "eight", "seven", "rm", "twelve", "rt", "O'Clock", "q"]
        # Set display variables based on display type
        if self.display_type == "4.0":
            self.default_x = 5
            self.y_start = 10
            self.line_space = 70
            self.letter_space = 40
        elif self.display_type == "7.3":
            self.default_x = 5
            self.y_start = 70
            self.line_space = 60
            self.letter_space = 50
        else:  # Assume 5.7 or fallback
            self.default_x = 20
            self.y_start = 40
            self.line_space = 65
            self.letter_space = 35
        self.scale = 5
        self.spacing = 2

    def setup(self):
        # Any setup logic if needed
        pass

    def teardown(self):
        # Any cleanup logic if needed
        self.time_string = None

    def update(self):
        try:
            ntptime.settime()
        except OSError:
            print("Unable to contact NTP server")
        current_t = self.rtc.datetime()
        TIMEZONE_OFFSET = 0
        utc_hour = current_t[4]
        pst_hour = (utc_hour + TIMEZONE_OFFSET) % 24
        pst_hour_display = pst_hour if pst_hour <= 12 else pst_hour - 12
        minutes = current_t[5]
        tstr = approx_time(pst_hour_display, minutes)
        self.time_string = tstr.split()

    def draw(self):
        graphics = self.graphics
        graphics.set_font("bitmap8")
        graphics.set_pen(1)
        graphics.clear()
        graphics.set_pen(6)
        x = self.default_x
        y = self.y_start
        for word in self.words:
            if self.time_string and word in self.time_string:
                graphics.set_pen(0)
            else:
                graphics.set_pen(graphics.create_pen(220, 220, 220))
            for letter in word:
                text_length = graphics.measure_text(
                    letter, self.scale, self.spacing)
                if not x + text_length <= self.WIDTH:
                    y += self.line_space
                    x = self.default_x
                graphics.text(letter.upper(), x, y, self.WIDTH,
                              scale=self.scale, spacing=self.spacing)
                x += self.letter_space
        graphics.update()

    @property
    def UPDATE_INTERVAL(self):
        return 15


# Module-level app instance for compatibility
app = WordClockApp()
