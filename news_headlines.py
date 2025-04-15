import gc
from urllib import urequest

import qrcode

from inky_app_base import InkyAppBase

# Uncomment one URL to use (Top Stories, World News and technology)
# URL = "https://feeds.bbci.co.uk/news/rss.xml"
# URL = "https://feeds.bbci.co.uk/news/world/rss.xml"
URL = "https://feeds.bbci.co.uk/news/technology/rss.xml"


def read_until(stream, find):
    result = b""
    while len(c := stream.read(1)) > 0:
        if c == find:
            return result
        result += c


def discard_until(stream, find):
    _ = read_until(stream, find)


def parse_xml_stream(s, accept_tags, group_by, max_items=3):
    tag = []
    text = b""
    count = 0
    current = {}

    while True:
        char = s.read(1)
        if len(char) == 0:
            break

        if char == b"<":
            next_char = s.read(1)

            # Discard stuff like <?xml vers...
            if next_char == b"?":
                discard_until(s, b">")
                continue

            # Detect <![CDATA
            elif next_char == b"!":
                s.read(1)  # Discard [
                discard_until(s, b"[")  # Discard CDATA[
                text = read_until(s, b"]")
                discard_until(s, b">")  # Discard ]>
                gc.collect()

            elif next_char == b"/":
                current_tag = read_until(s, b">")
                top_tag = tag[-1]

                # Populate our result dict
                if top_tag in accept_tags:
                    current[top_tag.decode("utf-8")] = text.decode("utf-8")

                # If we've found a group of items, yield the dict
                elif top_tag == group_by:
                    yield current
                    current = {}
                    count += 1
                    if count == max_items:
                        return
                tag.pop()
                text = b""
                gc.collect()
                continue

            else:
                current_tag = read_until(s, b">")
                if not current_tag.endswith(b"/"):
                    tag += [next_char + current_tag.split(b" ")[0]]
                    text = b""

        else:
            text += char


def measure_qr_code(size, code):
    w, h = code.get_size()
    module_size = int(size / w)
    return module_size * w, module_size


def draw_qr_code(ox, oy, size, code):
    size, module_size = measure_qr_code(size, code)
    graphics.set_pen(1)
    graphics.rectangle(ox, oy, size, size)
    graphics.set_pen(0)
    for x in range(size):
        for y in range(size):
            if code.get_module(x, y):
                graphics.rectangle(ox + x * module_size, oy +
                                   y * module_size, module_size, module_size)


# A function to get the data from an RSS Feed, this in case BBC News.
def get_rss():
    try:
        stream = urequest.urlopen(URL)
        output = list(parse_xml_stream(
            stream, [b"title", b"description", b"guid", b"pubDate"], b"item"))
        return output

    except OSError as e:
        print(e)
        return []


class NewsHeadlinesApp(InkyAppBase):
    def __init__(self, graphics=None, width=None, height=None):
        super().__init__(graphics, width, height)
        self.feed = []
        self.code = qrcode.QRCode()

    def setup(self):
        self.feed = []
        self.code = qrcode.QRCode()

    def teardown(self):
        self.feed = []
        self.code = None

    def update(self):
        self.feed = self.get_rss()

    def get_rss(self):
        try:
            stream = urequest.urlopen(URL)
            output = list(parse_xml_stream(
                stream, [b"title", b"description", b"guid", b"pubDate"], b"item"))
            return output
        except OSError as e:
            print(e)
            return []

    def draw(self):
        g = self.graphics
        g.set_font("bitmap8")
        g.set_pen(1)
        g.clear()
        g.set_pen(0)
        width = self.WIDTH
        height = self.HEIGHT
        feed = self.feed
        if feed and len(feed) > 1:
            g.set_pen(g.create_pen(200, 0, 0))
            g.rectangle(0, 0, width, 40)
            g.set_pen(1)
            g.text("Headlines from BBC News:", 10, 10, width - 10, 3)
            g.set_pen(4)
            g.text(feed[0]["title"], 10, 70, width - 150,
                   3 if g.measure_text(feed[0]["title"]) < width else 2)
            g.text(feed[1]["title"], 130, 260, width - 140,
                   3 if g.measure_text(feed[1]["title"]) < width else 2)
            g.set_pen(3)
            g.text(feed[0]["description"], 10, 135 if g.measure_text(
                feed[0]["title"]) < width else 90, width - 150, 2)
            g.text(feed[1]["description"], 130, 320 if g.measure_text(
                feed[1]["title"]) < width else 340, width - 145, 2)
            g.line(10, 215, width - 10, 215)
            self.code.set_text(feed[0]["guid"])
            draw_qr_code(width - 110, 65, 100, self.code)
            self.code.set_text(feed[1]["guid"])
            draw_qr_code(10, 265, 100, self.code)
            g.set_pen(g.create_pen(200, 0, 0))
            g.rectangle(0, height - 20, width, 20)
        else:
            self.show_error("Unable to display news feed!")
        g.update()

    @property
    def UPDATE_INTERVAL(self):
        return 90


# Module-level app instance for compatibility
app = NewsHeadlinesApp()
