"""
This example connects to the Carbon Intensity API to give you a regional
forecast of how your (UK) electricity is being generated and its carbon impact.

Carbon Intensity API only reports data from the UK National Grid.

Find out more about what the numbers mean at:
https://carbonintensity.org.uk/

Make sure to uncomment the correct size for your display!

"""

import inky_frame
import urequests

from inky_app_base import InkyAppBase

POSTCODE = "S9"
URL = "https://api.carbonintensity.org.uk/regional/postcode/" + str(POSTCODE)


class CarbonIntensityApp(InkyAppBase):
    def __init__(self):
        super().__init__()
        self.region = None
        self.forecast = None
        self.index = None
        self.power_list = [0]*9
        self.datetime_to = ["", ""]
        self.datetime_from = ["", ""]

    def teardown(self):
        pass

    def update(self):
        try:
            self.logger.info(f"Requesting URL: {URL}")
            r = urequests.get(URL)
            j = r.json()
            self.logger.info("Data obtained!")
            self.logger.debug(str(j))
            self.region = j["data"][0]["shortname"]
            self.forecast = j["data"][0]["data"][0]["intensity"]["forecast"]
            self.index = j["data"][0]["data"][0]["intensity"]["index"]
            self.power_list = [power['perc']
                               for power in j["data"][0]["data"][0]["generationmix"]]
            self.datetime_to = j["data"][0]["data"][0]["to"].split("T")
            self.datetime_from = j["data"][0]["data"][0]["from"].split("T")
            r.close()
        except Exception as e:
            self.logger.error(f"Error fetching carbon intensity data: {e}")
            self.show_error("Unable to fetch carbon data!")

    def draw(self):
        g = self.graphics
        w = self.width
        h = self.height
        g.set_pen(inky_frame.WHITE)
        g.clear()
        # draw lines
        g.set_pen(inky_frame.BLACK)
        g.line(0, int((h / 100) * 0), w, int((h / 100) * 0))
        g.line(0, int((h / 100) * 50), w, int((h / 100) * 50))
        g.set_font("bitmap8")
        g.text('100%', w - 40, 10, scale=2)
        g.text('50%', w - 40, int((h / 100) * 50 + 10), scale=2)
        # draw bars
        bar_colours = [
            inky_frame.ORANGE,
            inky_frame.RED,
            inky_frame.ORANGE,
            inky_frame.RED,
            inky_frame.BLUE,
            inky_frame.ORANGE,
            inky_frame.GREEN,
            inky_frame.GREEN,
            inky_frame.GREEN
        ]
        for idx, p in enumerate(self.power_list):
            g.set_pen(bar_colours[idx])
            g.rectangle(int(idx * w / 9), int(h - p * (h / 100)),
                        int(w / 9), int(h / 100 * p))
        # draw labels
        g.set_font('sans')
        # once in white for a background
        g.set_pen(inky_frame.WHITE)
        labels = ['biomass', 'coal', 'imports', 'gas',
                  'nuclear', 'other', 'hydro', 'solar', 'wind']
        g.set_thickness(4)
        for idx, label in enumerate(labels):
            g.text(f'{label}', int((idx * w / 9) + (w / 9) / 2),
                   h - 10, angle=270, scale=1)
        # again in black
        g.set_pen(inky_frame.BLACK)
        g.set_thickness(2)
        for idx, label in enumerate(labels):
            g.text(f'{label}', int((idx * w / 9) + (w / 9) / 2),
                   h - 10, angle=270, scale=1)
        # draw header
        g.set_thickness(3)
        g.set_pen(inky_frame.GREEN)
        if self.index in ['high', 'very high']:
            g.set_pen(inky_frame.RED)
        if self.index in ['moderate']:
            g.set_pen(inky_frame.ORANGE)
        g.set_font("sans")
        g.text('Carbon Intensity', 10, 35, scale=1.2, angle=0)
        # draw small text
        g.set_pen(inky_frame.BLACK)
        g.set_font("bitmap8")
        g.text(f'Region: {self.region}', int((w / 2) + 30), 10, scale=2)
        g.text(f'{self.forecast} gCO2/kWh ({self.index})',
               int((w / 2) + 30), 30, scale=2)
        g.text(f'{self.datetime_from[0]} {self.datetime_from[1]} to {self.datetime_to[1]}', int(
            (w / 2) + 30), 50, scale=2)
        g.update()

    @property
    def UPDATE_INTERVAL(self):
        return 240


# Module-level app instance for compatibility
app = CarbonIntensityApp()
