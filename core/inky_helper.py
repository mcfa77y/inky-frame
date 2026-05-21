import json
import math
import os
import time
from secrets import WIFI_PASSWORD, WIFI_SSID  # pylint: disable=no-name-in-module

import inky_frame
import network
from machine import PWM, Pin, Timer
from pcf85063a import PCF85063A
from pimoroni_i2c import PimoroniI2C

from .logger import Logger

inky_helper_logger = Logger(default_context={"app": "inky_helper"})

# Pin setup for VSYS_HOLD needed to sleep and wake.
HOLD_VSYS_EN_PIN = 2
hold_vsys_en_pin = Pin(HOLD_VSYS_EN_PIN, Pin.OUT)

# intialise the pcf85063a real time clock chip
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5
i2c = PimoroniI2C(I2C_SDA_PIN, I2C_SCL_PIN, 100000)
rtc = PCF85063A(i2c)

led_warn = Pin(6, Pin.OUT)

# set up for the network LED
network_led_pwm = PWM(Pin(7))
network_led_pwm.freq(1000)
network_led_pwm.duty_u16(0)


# set the brightness of the network led
def network_led(brightness):
    inky_helper_logger.debug(
        f"network_led called with brightness={brightness}")
    brightness = max(0, min(100, brightness))  # clamp to range
    # gamma correct the brightness (gamma 2.8)
    value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)
    inky_helper_logger.debug(f"Setting network LED PWM duty to {value}")
    network_led_pwm.duty_u16(value)


network_led_timer = Timer(-1)
network_led_pulse_speed_hz = 1


def network_led_callback(t):
    inky_helper_logger.debug("network_led_callback triggered")
    # updates the network led brightness based on a sinusoid seeded by the current time
    brightness = (math.sin(time.ticks_ms() * math.pi * 2 /
                  (1000 / network_led_pulse_speed_hz)) * 40) + 60
    value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)
    inky_helper_logger.debug(f"network_led_callback sets PWM duty to {value}")
    network_led_pwm.duty_u16(value)


# set the network led into pulsing mode
def pulse_network_led(speed_hz=1):
    inky_helper_logger.debug(
        f"pulse_network_led called with speed_hz={speed_hz}")
    global network_led_pulse_speed_hz
    network_led_pulse_speed_hz = speed_hz
    network_led_timer.deinit()
    network_led_timer.init(period=50, mode=Timer.PERIODIC,
                           callback=network_led_callback)


# turn off the network led and disable any pulsing animation that's running
def stop_network_led():
    inky_helper_logger.debug("stop_network_led called")
    network_led_timer.deinit()
    network_led_pwm.duty_u16(0)


# Wave light pattern for button LEDs using PWM
wave_timer = Timer(-1)
wave_position = 0.0
wave_direction = 1
wave_speed = 0.1

# PWM objects for button LEDs
button_pwms = []

def init_button_pwms():
    """Initialize PWM for button LEDs"""
    global button_pwms
    if not button_pwms:  # Only initialize once
        try:
            # Inky Frame button LED pin assignments (based on hardware)
            button_led_pins = [11, 12, 13, 14, 15]  # Pins for buttons A, B, C, D, E
            button_pwms = [PWM(Pin(pin)) for pin in button_led_pins]
            for pwm in button_pwms:
                pwm.freq(1000)  # 1kHz frequency
                pwm.duty_u16(0)  # Start with LEDs off
            inky_helper_logger.debug(f"Initialized PWM for {len(button_pwms)} button LEDs")
        except Exception as e:
            inky_helper_logger.error(f"Failed to initialize button PWMs: {e}")
            # Fallback to regular LED control
            button_pwms = []

def wave_led_callback(t):
    """Creates a smooth PWM wave pattern across buttons A through E"""
    global wave_position, wave_direction
    
    if not button_pwms:
        # Fallback to simple on/off pattern if PWM failed
        clear_button_leds()
        buttons = [inky_frame.button_a, inky_frame.button_b, inky_frame.button_c, inky_frame.button_d, inky_frame.button_e]
        step = int(wave_position)
        for i in range(len(buttons)):
            distance = abs(i - step)
            if distance <= 1:
                buttons[i].led_on()
    else:
        # PWM wave pattern
        import math
        for i, pwm in enumerate(button_pwms):
            # Calculate distance from wave center
            distance = abs(i - wave_position)
            
            # Create a smooth wave with gaussian-like falloff
            if distance <= 2.0:  # Wave width of 4 LEDs
                # Use cosine for smooth wave shape
                brightness = math.cos(distance * math.pi / 4) ** 2
                brightness = max(0, brightness)  # Ensure non-negative
                duty = int(brightness * 65535)  # Convert to 16-bit duty cycle
                pwm.duty_u16(duty)
            else:
                pwm.duty_u16(0)  # Turn off distant LEDs
    
    # Move wave position
    wave_position += wave_direction * wave_speed
    if wave_position >= 4.0:  # 5 buttons (0-4)
        wave_direction = -1
    elif wave_position <= 0.0:
        wave_direction = 1

def start_wave_pattern():
    """Start the PWM wave LED pattern"""
    inky_helper_logger.debug("start_wave_pattern called")
    global wave_position, wave_direction
    wave_position = 0.0
    wave_direction = 1
    
    # Initialize PWM if not already done
    init_button_pwms()
    
    wave_timer.deinit()
    wave_timer.init(period=50, mode=Timer.PERIODIC, callback=wave_led_callback)

def stop_wave_pattern():
    """Stop the wave LED pattern and clear all LEDs"""
    inky_helper_logger.debug("stop_wave_pattern called")
    wave_timer.deinit()
    
    # Turn off PWM LEDs
    if button_pwms:
        for pwm in button_pwms:
            pwm.duty_u16(0)
    
    # Also clear regular LEDs as fallback
    clear_button_leds()


def sleep(minutes: int):
    # inky_helper_logger.debug(f"sleep called for {minutes} minutes")
    # Time to have a little nap until the next update
    rtc.clear_timer_flag()
    rtc.set_timer(minutes, ttp=rtc.TIMER_TICK_1_OVER_60HZ)
    rtc.enable_timer_interrupt(True)

    # Set the HOLD VSYS pin to an input
    # this allows the device to go into sleep mode when on battery power.
    hold_vsys_en_pin.init(Pin.IN)
    # inky_helper_logger.debug("Set HOLD_VSYS_EN_PIN to input for sleep mode")
    # Regular time.sleep for those powering from USB
    time.sleep(60 * minutes)


# Turns off the button LEDs
def clear_button_leds():
    inky_helper_logger.debug("clear_button_leds called")
    inky_frame.button_a.led_off()
    inky_frame.button_b.led_off()
    inky_frame.button_c.led_off()
    inky_frame.button_d.led_off()
    inky_frame.button_e.led_off()


def network_connect():
    ssid = WIFI_SSID
    password = WIFI_PASSWORD
    inky_helper_logger.debug(f"network_connect called with SSID={ssid}")
    # Enable the Wireless
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Number of attempts to make before timeout
    max_wait = 10

    # Sets the Wireless LED pulsing and attempts to connect to your local network.
    pulse_network_led()
    wlan.config(pm=0xa11140)  # Turn WiFi power saving off for some slow APs
    wlan.connect(ssid, password)
    inky_helper_logger.debug("Attempting WiFi connection")

    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        inky_helper_logger.debug(
            f"Waiting for connection... attempts left: {max_wait}")
        time.sleep(1)

    stop_network_led()
    network_led_pwm.duty_u16(30000)

    # Handle connection error. Switches the Warn LED on.
    status = wlan.status()
    if status != 3:
        status_reasons = {
            0: "Link down / idle",
            1: "Connecting",
            2: "Connected, no IP",
            -1: "Generic connection failure",
            -2: "SSID not found",
            -3: "Bad authentication (wrong password)"
        }
        reason = status_reasons.get(status, "Unknown error")
        inky_helper_logger.debug(
            f"WiFi connection failed with status {status} ({reason})")
        stop_network_led()
        led_warn.on()
    else:
        inky_helper_logger.debug("WiFi connection successful")


state = {"run": None}
app = None


def file_exists(filename):
    inky_helper_logger.debug(f"file_exists called with filename={filename}")
    try:
        exists = (os.stat(filename)[0] & 0x4000) == 0
        inky_helper_logger.debug(f"file_exists: {filename} exists: {exists}")
        return exists
    except OSError as e:
        inky_helper_logger.debug(
            f"file_exists: {filename} not found, OSError: {e}")
        return False


def clear_state():
    inky_helper_logger.debug("clear_state called")
    if file_exists("state.json"):
        os.remove("state.json")
        inky_helper_logger.debug("state.json removed")
    else:
        inky_helper_logger.debug("state.json does not exist")


def save_state(data):
    inky_helper_logger.debug(f"save_state called with data={data}")
    with open("/state.json", "w") as f:
        f.write(json.dumps(data))
        f.flush()
    inky_helper_logger.debug("State saved to /state.json")


def load_state():
    inky_helper_logger.debug("load_state called")
    global state
    data = json.loads(open("/state.json", "r").read())
    if type(data) is dict:
        state = data
        inky_helper_logger.debug(f"State loaded: {state}")
    else:
        inky_helper_logger.debug("State loaded is not a dict")


def update_state(running):
    inky_helper_logger.debug(f"update_state called with running={running}")
    global state
    state['run'] = running
    save_state(state)


def launch_app(app_name):
    inky_helper_logger.debug(f"launch_app called with app_name={app_name}")
    global app
    app_module = __import__(app_name)
    inky_helper_logger.debug(f"Imported module {app_name}: {dir(app_module)}")
    app = getattr(app_module, "app")
    inky_helper_logger.debug(f"App object: {app}")
    update_state(app_name)


def get_inky_frame_type(height):
    inky_helper_logger.debug(
        f"get_inky_frame_type called with height={height}")
    """Return the Inky Frame type as a string based on the display height."""
    if height == 448:
        inky_helper_logger.debug("Frame type is 5.7")
        return "5.7"
    elif height == 480:
        inky_helper_logger.debug("Frame type is 7.3")
        return "7.3"
    elif height == 320:
        inky_helper_logger.debug("Frame type is 4.0")
        return "4.0"
    else:
        inky_helper_logger.debug("Frame type is unknown")
        return "unknown"
