import time
import math
import gc
import digitalio
import audioio
import audiocore
import busio
import board
from analogio import AnalogIn
import neopixel
import adafruit_lis3dh
from adafruit_led_animation.animation.rainbow import Rainbow

HIT_THRESHOLD = 350  # 250
SWING_THRESHOLD = 125

NUM_PIXELS = 60  # NeoPixel strip length (in pixels)
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10
SWITCH_PIN = board.D9

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

red_led = digitalio.DigitalInOut(board.D11)
red_led.direction = digitalio.Direction.OUTPUT
green_led = digitalio.DigitalInOut(board.D12)
green_led.direction = digitalio.Direction.OUTPUT
blue_led = digitalio.DigitalInOut(board.D13)
blue_led.direction = digitalio.Direction.OUTPUT

audio = audioio.AudioOut(board.A0)  # Speaker
mode = 0  # Initial mode = OFF

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1.0)
strip.fill(0)  # NeoPixels off ASAP on startup
strip.show()

switch = digitalio.DigitalInOut(SWITCH_PIN)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

toggle = digitalio.DigitalInOut(board.A2)
toggle.direction = digitalio.Direction.INPUT
toggle.pull = digitalio.Pull.UP
state = toggle.value

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

vbat_voltage = AnalogIn(board.VOLTAGE_MONITOR)

def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2

def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    print("playing", name)
    try:
        wave_file = open("sounds/" + name + ".wav", "rb")
        wave = audiocore.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except:
        return


def power(sound, duration, reverse):
    """
    Animate NeoPixels with accompanying sound effect for power on / off.
    @param sound:    sound name (similar format to play_wav() above)
    @param duration: estimated duration of sound, in seconds (>0.0)
    @param reverse:  if True, do power-off effect (reverses animation)
    """

    if reverse:
        prev = NUM_PIXELS
    else:
        prev = 0
    gc.collect()  # Tidy up RAM now so animation's smoother
    start_time = time.monotonic()  # Save audio start time
    play_wav(sound)
    while True:
        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:  # Past sound duration?
            break  # Stop animating
        fraction = elapsed / duration  # Animation time, 0.0 to 1.0
        if reverse:
            fraction = 1.0 - fraction  # 1.0 to 0.0 if reverse
        fraction = math.pow(fraction, 0.5)  # Apply nonlinear curve
        threshold = int((NUM_PIXELS * fraction) + 0.5)

        num = threshold - prev  # Number of pixels to light on this pass
        if num != 0:
            if reverse:
                strip[threshold:prev] = [0] * -num
            else:
                strip[prev:threshold] = [COLOR_IDLE] * num
            strip.show()
            # NeoPixel writes throw off time.monotonic() ever so slightly
            # because interrupts are disabled during the transfer.
            # We can compensate somewhat by adjusting the start time
            # back by 30 microseconds per pixel.
            start_time -= NUM_PIXELS * 0.00003
            prev = threshold

    if reverse:
        strip.fill(0)  # At end, ensure strip is off
    else:
        strip.fill(COLOR_IDLE)  # or all pixels set on
    strip.show()
    while audio.playing:  # Wait until audio done
        pass


def mix(color_1, color_2, weight_2):
    """
    Blend between two colors with a given ratio.
    @param color_1:  first color, as an (r,g,b) tuple
    @param color_2:  second color, as an (r,g,b) tuple
    @param weight_2: Blend weight (ratio) of second color, 0.0 to 1.0
    @return: (r,g,b) tuple, blended color
    """
    if weight_2 < 0.0:
        weight_2 = 0.0
    elif weight_2 > 1.0:
        weight_2 = 1.0
    weight_1 = 1.0 - weight_2
    return (
        int(color_1[0] * weight_1 + color_2[0] * weight_2),
        int(color_1[1] * weight_1 + color_2[1] * weight_2),
        int(color_1[2] * weight_1 + color_2[2] * weight_2),
    )

def set_button_color(r, g, b):
    red_led.value = r
    green_led.value = g
    blue_led.value = b

def set_color(NEW_COLOR):
    global COLOR, COLOR_IDLE, COLOR_SWING
    COLOR = NEW_COLOR
    COLOR_IDLE = (int(NEW_COLOR[0] / 1), int(NEW_COLOR[1] / 1), int(NEW_COLOR[2] / 1))
    COLOR_SWING = NEW_COLOR

    if (NEW_COLOR == GREEN_COLOR):
        set_button_color(False, True, False)
    elif (NEW_COLOR == PURPLE_COLOR or NEW_COLOR == CYAN_COLOR):
        set_button_color(False, False, True)
    elif (NEW_COLOR == RAINBOW_COLOR):
        set_button_color(False, False, False)
    else:
        set_button_color(True, False, False)


# "Idle" color is 1/4 brightness, "swinging" color is full brightness...
# CUSTOMIZE YOUR COLOR HERE:
# (red, green, blue) -- each 0 (off) to 255 (brightest)
RED_COLOR = (255, 0, 0)  # red
PURPLE_COLOR = (100, 0, 255)  # purple
CYAN_COLOR = (0, 100, 255)  # cyan
GREEN_COLOR = (0, 255, 0)  # cyan
RAINBOW_COLOR = (255, 255, 255)  # placeholder
COLOR = RED_COLOR
COLOR_IDLE = COLOR
COLOR_SWING = COLOR

set_color(COLOR)
COLOR_HIT = (255, 255, 255)  # "hit" color is white
rainbow = Rainbow(strip, speed=0.1, period=2)
# while True:
#     rainbow.animate()

button_push = False
while True:
    # toggle.value is true, means the button has been released. I think we got the wires mixed up
    if mode != 0 and toggle.value:
        button_push = False

    # toggle.value is false, and we haven't already processed a button push,
    if mode != 0 and not toggle.value and not button_push:
        # Mark the button push detected
        button_push = True
        print("Button pushed")

        # Rotate through colours and button colours
        if COLOR == RED_COLOR:
            print("Changed to PURPLE")
            set_color(PURPLE_COLOR)
        elif COLOR == PURPLE_COLOR:
            print("Changed to CYAN")
            set_color(CYAN_COLOR)
        elif COLOR == CYAN_COLOR:
            print("Changed to GREEN")
            set_color(GREEN_COLOR)
        elif COLOR == GREEN_COLOR:
            print("Changed to Rainbow")
            set_color(RAINBOW_COLOR)
        else:
            print("Changed to RED")
            set_color(RED_COLOR)

        strip.fill(COLOR_IDLE)  # Set to idle color
        strip.show()

    if not switch.value:  # button pressed?
        if mode == 0:  # If currently off...
            #enable.value = True
            power("on", 1.7, False)  # Power up!
            play_wav("idle", loop=True)  # Play background hum sound
            mode = 1  # ON (idle) mode now
        else:  # else is currently on...
            power("off", 1.15, True)  # Power down
            mode = 0  # OFF mode now
            #enable.value = False
        while not switch.value:  # Wait for button release
            time.sleep(0.2)  # to avoid repeated triggering

    elif mode >= 1:  # If not OFF mode...
        x, y, z = accel.acceleration  # Read accelerometer
        accel_total = x * x + z * z
        if COLOR == RAINBOW_COLOR:
            rainbow.animate()
        # (Y axis isn't needed for this, assuming Hallowing is mounted
        # sideways to stick.  Also, square root isn't needed, since we're
        # just comparing thresholds...use squared values instead, save math.)
        if accel_total > HIT_THRESHOLD:  # Large acceleration = HIT
            TRIGGER_TIME = time.monotonic()  # Save initial time of hit
            play_wav("hit")  # Start playing 'hit' sound
            COLOR_ACTIVE = COLOR_HIT  # Set color to fade from
            mode = 3  # HIT mode
        elif mode == 1 and accel_total > SWING_THRESHOLD:  # Mild = SWING
            TRIGGER_TIME = time.monotonic()  # Save initial time of swing
            play_wav("swing")  # Start playing 'swing' sound
            COLOR_ACTIVE = COLOR_SWING  # Set color to fade from
            mode = 2  # SWING mode
        elif mode > 1:  # If in SWING or HIT mode...
            if audio.playing:  # And sound currently playing...
                if COLOR != RAINBOW_COLOR:
                    blend = time.monotonic() - TRIGGER_TIME  # Time since triggered
                    if mode == 2:  # If SWING,
                        blend = abs(0.5 - blend) * 2.0  # ramp up, down
                    strip.fill(mix(COLOR_ACTIVE, COLOR_IDLE, blend))
                    strip.show()
            else:  # No sound now, but still MODE > 1
                play_wav("idle", loop=True)  # Resume background hum
                if COLOR != RAINBOW_COLOR:
                    strip.fill(COLOR_IDLE)  # Set to idle color
                    strip.show()
                mode = 1  # IDLE mode now

    #battery_voltage = get_voltage(vbat_voltage)
    #print("VBat voltage: {:.2f}".format(battery_voltage))
    #if battery_voltage > 4:
    #    set_button_color(False, True, False)
    #elif battery_voltage > 3.7:
    #    set_button_color(False, False, True)
    #else:
    #    set_button_color(True, False, False)
    #time.sleep(10)
