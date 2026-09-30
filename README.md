# Raspberry Pi Pico Benchtop Centrifuge Controller

A MicroPython-based controller for a small benchtop centrifuge built around a Raspberry Pi Pico.

The project combines embedded programming, motor control, analog user inputs, an OLED interface, and a high-current motor driver. The controller lets the user set a motor command and run time, start or stop the centrifuge with a toggle switch, and monitor the current operating state on an SSD1306 OLED display.

> \*\*Note:\*\* The displayed 0–100% value represents the PWM motor command, not measured RPM. The current version does not use closed-loop speed feedback.

## Features

* Adjustable motor command from 0–100% using a potentiometer
* Adjustable run time from 5 seconds to 10 minutes
* Toggle-switch start/stop control
* Soft motor acceleration and deceleration
* OLED display showing operating mode, switch state, motor command, and remaining time
* Automatic stop when the selected run time expires
* Manual soft stop if the toggle switch is turned off during a run
* Simple IDLE/RUN state-based control logic
* Emergency motor shutdown if the program is interrupted or raises an exception

## Hardware

The controller was developed around:

* Raspberry Pi Pico
* BTS7960 motor driver
* DC motor
* SSD1306 128×64 I2C OLED
* Two potentiometers
* One toggle switch
* 5 V buck converter for the Pico and BTS7960 logic supply

## Pin Mapping

|Function|Raspberry Pi Pico Pin|Connection|
|-|-|-|
|Motor PWM|GP15|BTS7960 RPWM|
|Motor enable|GP14|BTS7960 R\_EN|
|Motor enable|GP13|BTS7960 L\_EN|
|Speed/PWM control|GP26 / ADC0|Potentiometer wiper|
|Run-time control|GP27 / ADC1|Potentiometer wiper|
|Start/stop switch|GP16|Toggle switch to GND|
|OLED SDA|GP0|SSD1306 SDA|
|OLED SCL|GP1|SSD1306 SCL|

The BTS7960 LPWM input is not used because the motor is operated in one direction only.

## How it Works

### 1\. User inputs

The two potentiometers are read through the Pico's ADC inputs.

The first potentiometer is mapped to a 16-bit PWM duty-cycle command. The second is mapped to a run time between 5 seconds and 10 minutes.

### 2\. Motor control

The motor is driven through the BTS7960 using a 20 kHz PWM signal.

Instead of immediately jumping between zero and the requested command, `ramp\_motor()` changes the PWM duty cycle progressively. This provides a softer startup and shutdown.

### 3\. State control

The controller uses two primary states:

* `IDLE` — motor output is zero while the user selects the desired settings.
* `RUN` — the motor operates until the timer expires or the user switches the system off.

The toggle switch is active-low. The program detects the transition from OFF to ON to begin a run and the transition from ON to OFF to request a soft stop.

### 4\. OLED interface

The SSD1306 display provides a simple user interface showing:

* Current operating mode
* Toggle-switch state
* Motor command as a percentage
* Remaining run time in `MM:SS`
* A graphical motor-command bar

### 5\. Shutdown behaviour

When the timer reaches zero, the program ramps the motor command down to zero and returns to `IDLE`.

Turning the toggle switch off during a run performs the same controlled ramp-down.

The top-level exception handlers also set the PWM output to zero before stopping or re-raising an unexpected error.

## Project Structure

```text
centrifuge-controller/
├── main.py       # MicroPython control program
└── README.md     # Project documentation
```

## Code Overview

The main program is organized into several sections:

* Hardware and pin configuration
* Centrifuge operating parameters
* SSD1306 display driver/interface
* ADC-to-PWM and ADC-to-time conversion functions
* Motor ramping function
* OLED user-interface function
* Main IDLE/RUN control loop

This separation made it easier to test individual parts of the controller and modify parameters during prototyping.

## 

