import gc
from urllib import urequest  # type: ignore[attr-defined]

import qrcode

from core.inky_app_base import InkyAppBase

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
    return result


def discard_until(stream, find):
    _ = read_until(stream, find)


def _read_cdata(s):
    s.read(1)  # Discard [
    discard_until(s, b"[")  # Discard CDATA[
    text = read_until(s, b"]")
    discard_until(s, b">")  # Discard ]>
    gc.collect()
    return text


def _handle_closing_tag(s, tag, text, accept_tags, group_by, current):
    discard_until(s, b">")
    if not tag:
        return False
    top_tag = tag.pop()
    if top_tag in accept_tags:
        current[top_tag.decode("utf-8")] = text.decode("utf-8")
    gc.collect()
    return top_tag == group_by


def _handle_open_tag(s, next_char, tag):
    current_tag = read_until(s, b">")
    if not current_tag.endswith(b"/"):
        tag.append(next_char + current_tag.split(b" ")[0])


def _handle_tag(s, tag, text, accept_tags, group_by, current):
    next_char = s.read(1)
    if next_char == b"?":
        discard_until(s, b">")
        return text, False
    if next_char == b"!":
        return _read_cdata(s), False
    if next_char == b"/":
        is_grouped = _handle_closing_tag(s, tag, text, accept_tags, group_by, current)
        return b"", is_grouped
    _handle_open_tag(s, next_char, tag)
    return b"", False


def parse_xml_stream(s, accept_tags, group_by, max_items=3):
    tag = []
    text = b""
    count = 0
    current = {}

    while len(char := s.read(1)) > 0:
        if char == b"<":
            text, item_ready = _handle_tag(s, tag, text, accept_tags, group_by, current)
            if item_ready:
                yield current
                current = {}
                count += 1
                if count == max_items:
                    return
        else:
            text += char


def measure_qr_code(size, code):
    w, _ = code.get_size()
    module_size = int(size / w)
    return module_size * w, module_size


def draw_qr_code(graphics, ox, oy, size, code):
    size, module_size = measure_qr_code(size, code)
    graphics.set_pen(1)
    graphics.rectangle(ox, oy, size, size)
    graphics.set_pen(0)
    for x in range(size):
        for y in range(size):
            if code.get_module(x, y):
                graphics.rectangle(ox + x * module_size, oy + y * module_size, module_size, module_size)


# A function to get the data from an RSS Feed, this in case BBC News.
def get_rss():
    try:
        stream = urequest.urlopen(URL)
        output = list(parse_xml_stream(stream, [b"title", b"description", b"guid", b"pubDate"], b"item"))
        return output

    except OSError as e:
        print(e)
        return []


class NewsHeadlinesApp(InkyAppBase):
    def __init__(self):
        super().__init__()
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
            output = list(parse_xml_stream(stream, [b"title", b"description", b"guid", b"pubDate"], b"item"))
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
        width = self.width
        height = self.height
        feed = self.feed
        if feed and len(feed) > 1:
            g.set_pen(g.create_pen(200, 0, 0))
            g.rectangle(0, 0, width, 40)
            g.set_pen(1)
            g.text("Headlines from BBC News:", 10, 10, width - 10, 3)
            g.set_pen(4)
            g.text(feed[0]["title"], 10, 70, width - 150, 3 if g.measure_text(feed[0]["title"]) < width else 2)
            g.text(feed[1]["title"], 130, 260, width - 140, 3 if g.measure_text(feed[1]["title"]) < width else 2)
            g.set_pen(3)
            g.text(feed[0]["description"], 10, 135 if g.measure_text(feed[0]["title"]) < width else 90, width - 150, 2)
            g.text(
                feed[1]["description"], 130, 320 if g.measure_text(feed[1]["title"]) < width else 340, width - 145, 2
            )
            g.line(10, 215, width - 10, 215)
            if self.code is not None:
                self.code.set_text(feed[0]["guid"])
                draw_qr_code(g, width - 110, 65, 100, self.code)
                self.code.set_text(feed[1]["guid"])
                draw_qr_code(g, 10, 265, 100, self.code)
            g.set_pen(g.create_pen(200, 0, 0))
            g.rectangle(0, height - 20, width, 20)
        else:
            self.show_error("Unable to display news feed!")
        g.update()

    @property
    def update_interval(self):
        return 90


# Module-level app instance for compatibility
app = NewsHeadlinesApp()
