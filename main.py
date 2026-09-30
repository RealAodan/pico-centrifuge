"""Some hardware parameters and code implementation were chosen from online documentation,
example projects, and community resources, then tested for this project."""

from machine import Pin, PWM, ADC, I2C  # MicroPython hardware module
import time
import framebuf


# Pin configuration
# BTS7960 driver
MOTOR_PWM_PIN = 15       # GP15 -> RPWM
MOTOR_REN_PIN = 14       # GP14 -> R_EN
MOTOR_LEN_PIN = 13       # GP13 -> L_EN

# User control
START_SWITCH_PIN = 16    # GP16 -> Start/Stop switch
SPEED_POT_PIN = 26       # GP26/ADC0 -> Speed pot
TIME_POT_PIN = 27        # GP27/ADC1 -> Time pot

# SSD1306 display (OLED)
OLED_SDA_PIN = 0         # GP0 -> SDA
OLED_SCL_PIN = 1         # GP1 -> SCL

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDRESS = 0x3C


# Centrifuge settings

# PWM settings
PWM_FREQUENCY_HZ = 20_000
ADC_MAX = 65535

# Run time range
MIN_TIME_S = 5           # Min 5 seconds
MAX_TIME_S = 10 * 60     # Max 10 minutes

# PWM output range for motor speed
MIN_DUTY = 1500 # Lowest motor power command to avoid motor buzzing (This seems to be the lowest value to avoid a weird operation)
MAX_DUTY = 65535 # Max PWM possible 

# Motor acceleration and deceleration. Ramp values were based on online help.
RAMP_STEP = 800          
RAMP_DELAY_MS = 5        

# Program states
STATE_IDLE = "IDLE"
STATE_RUN = "RUN"


# Motor PWM output
motor_pwm = PWM(Pin(MOTOR_PWM_PIN))
motor_pwm.freq(PWM_FREQUENCY_HZ)
motor_pwm.duty_u16(0)

# BTS7960 enable pins
motor_right_enable = Pin(MOTOR_REN_PIN, Pin.OUT, value=1)
motor_left_enable = Pin(MOTOR_LEN_PIN, Pin.OUT, value=1)

# Not using the LPWM since the motor spins only one way

# Pots
speed_pot = ADC(Pin(SPEED_POT_PIN))
time_pot = ADC(Pin(TIME_POT_PIN))

# Toggle switch
# 1 = switch OFF
# 0 = switch ON (connected to GND)
start_switch = Pin(START_SWITCH_PIN, Pin.IN, Pin.PULL_UP)

# I2C connection for OLED
i2c = I2C(
    0,
    sda=Pin(OLED_SDA_PIN),
    scl=Pin(OLED_SCL_PIN),
    freq=400_000
)


# Reference:
# https://github.com/micropython/micropython-lib/blob/master/
# micropython/drivers/display/ssd1306/ssd1306.py

# SSD1306 OLED driver


class SSD1306_I2C(framebuf.FrameBuffer):

    def __init__(
        self,
        width,
        height,
        i2c,
        address=OLED_ADDRESS
    ):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.address = address

        self.buffer = bytearray(
            self.width * self.height // 8
        )

        super().__init__(
            self.buffer,
            self.width,
            self.height,
            framebuf.MONO_VLSB
        )

        self.init_display()

    def write_cmd(self, command):
        """Send a command byte to the OLED."""
        self.i2c.writeto(
            self.address,
            b'\x00' + bytearray([command])
        )

    def write_data(self, buffer):
        """Send display to the OLED."""
        self.i2c.writeto(
            self.address,
            b'\x40' + buffer
        )

    def init_display(self):
        """Configure and turn on the SSD1306 display."""

        for command in (
            0xAE,        # Display OFF
            0x20, 0x00,  # Horizontal addressing mode
            0xB0,        # Page 0
            0xC8,        # COM scan direction remapped
            0x00,        # Low column
            0x10,        # High column
            0x40,        # Display start line
            0x81, 0x7F,  # Contrast
            0xA1,        # Segment remap
            0xA6,        # Normal display
            0xA8, 0x3F,  # Multiplex ratio
            0xA4,        # Resume RAM display
            0xD3, 0x00,  # Display offset
            0xD5, 0x80,  # Display clock
            0xD9, 0xF1,  # Pre-charge
            0xDA, 0x12,  # COM pin configuration
            0xDB, 0x40,  # VCOMH level
            0x8D, 0x14,  # Charge pump
            0xAF         # Display ON
        ):
            self.write_cmd(command)

        self.fill(0)
        self.show()

    def show(self):
        """Send the framebuffer contents to the OLED."""

        for page in range(self.height // 8):

            self.write_cmd(0xB0 + page)
            self.write_cmd(0x00)
            self.write_cmd(0x10)

            start = page * self.width
            end = start + self.width

            self.write_data(self.buffer[start:end])


oled = SSD1306_I2C(
    OLED_WIDTH,
    OLED_HEIGHT,
    i2c
)



# Defined functions

def adc_to_duty(adc_value):


    return int(
        MIN_DUTY
        + (
            adc_value
            * (MAX_DUTY - MIN_DUTY)
            // ADC_MAX
        )
    )


def adc_to_time_ms(adc_value):


    seconds = (
        MIN_TIME_S
        + (
            adc_value
            * (MAX_TIME_S - MIN_TIME_S)
            // ADC_MAX
        )
    )

    return seconds * 1000


def ramp_motor(target_duty):


    current_duty = motor_pwm.duty_u16()

    if current_duty == target_duty:
        return

    if target_duty > current_duty:
        step = RAMP_STEP
    else:
        step = -RAMP_STEP

    while (
        (step > 0 and current_duty < target_duty)
        or
        (step < 0 and current_duty > target_duty)
    ):

        current_duty += step

        if step > 0 and current_duty > target_duty:
            current_duty = target_duty

        if step < 0 and current_duty < target_duty:
            current_duty = target_duty

        current_duty = max(
            0,
            min(MAX_DUTY, current_duty)
        )

        motor_pwm.duty_u16(current_duty)

        time.sleep_ms(RAMP_DELAY_MS)


def draw_ui(
    mode,
    time_left_ms,
    switch_on,
    target_speed_percent
):

    oled.fill(0)

    # Current operating mode
    oled.text(
        "Mode: {}".format(mode),
        0,
        0
    )

    oled.text(
        "SW: {}".format(
            "ON" if switch_on else "OFF"
        ),
        80,
        0
    )

    speed_percent = max(
        0,
        min(100, target_speed_percent)
    )

    oled.text(
        "Speed: {}%".format(speed_percent),
        0,
        14
    )

    # Speed bar
    bar_width = int(
        speed_percent
        * (OLED_WIDTH - 4)
        / 100
    )

    oled.rect(
        0,
        26,
        OLED_WIDTH - 2,
        10,
        1
    )

    oled.fill_rect(
        1,
        27,
        bar_width,
        8,
        1
    )

    # To convert remaining ms to MM:SS.
    seconds_left = max(
        0,
        time_left_ms // 1000
    )

    minutes = seconds_left // 60
    seconds = seconds_left % 60

    oled.text(
        "Time: {:02d}:{:02d}".format(
            minutes,
            seconds
        ),
        0,
        42
    )

    oled.text(
        "Toggle SW to RUN",
        0,
        56
    )

    oled.show()



# The main control loop


def main():

    current_state = STATE_IDLE

    previous_switch = start_switch.value()

    run_start_ms = 0
    run_time_ms = 0
    target_duty = 0

    while True:

        # Read user inputs

        speed_adc = speed_pot.read_u16()
        time_adc = time_pot.read_u16()

        switch_value = start_switch.value()

        target_duty = adc_to_duty(speed_adc)
        run_time_ms = adc_to_time_ms(time_adc)

        target_speed_percent = int(
            speed_adc * 100 // ADC_MAX
        )


        # Detect switch


        switch_turned_on = (
            previous_switch == 1
            and switch_value == 0
        )

        switch_turned_off = (
            previous_switch == 0
            and switch_value == 1
        )

        previous_switch = switch_value

        current_time_ms = time.ticks_ms()


        if current_state == STATE_IDLE:

            motor_pwm.duty_u16(0)

            draw_ui(
                STATE_IDLE,
                run_time_ms,
                switch_value == 0,
                target_speed_percent
            )

            if switch_turned_on:

                draw_ui(
                    "START",
                    run_time_ms,
                    True,
                    target_speed_percent
                )


                ramp_motor(target_duty)
                run_start_ms = time.ticks_ms()

                current_state = STATE_RUN


        # RUN

        elif current_state == STATE_RUN:

            elapsed_ms = time.ticks_diff(
                current_time_ms,
                run_start_ms
            )

            time_left_ms = max(
                0,
                run_time_ms - elapsed_ms
            )

            motor_pwm.duty_u16(target_duty)

            draw_ui(
                STATE_RUN,
                time_left_ms,
                switch_value == 0,
                target_speed_percent
            )


            if time_left_ms <= 0:

                draw_ui(
                    "STOP",
                    0,
                    switch_value == 0,
                    target_speed_percent
                )

                ramp_motor(0)

                motor_pwm.duty_u16(0)

                current_state = STATE_IDLE

            elif switch_turned_off:

                draw_ui(
                    "ABORT",
                    time_left_ms,
                    False,
                    target_speed_percent
                )

                ramp_motor(0)

                motor_pwm.duty_u16(0)

                current_state = STATE_IDLE

        time.sleep_ms(30)

# Program start

try:
    main()

except KeyboardInterrupt:
    motor_pwm.duty_u16(0)

except Exception:
    motor_pwm.duty_u16(0)
    raise