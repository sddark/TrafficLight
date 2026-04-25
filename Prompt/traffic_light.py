"""
Raspberry Pi Traffic Light Controller
======================================
Hardware:
  - Red LED    → GPIO 17 → 330Ω resistor → GND
  - Yellow LED → GPIO 27 → 330Ω resistor → GND
  - Green LED  → GPIO 22 → 330Ω resistor → GND
  - Button     → GPIO 18 → GND  (internal pull-up enabled)

Wiring diagram:
  RPi GPIO 17 ──[330Ω]──► Red LED anode   │ cathode → GND
  RPi GPIO 27 ──[330Ω]──► Yellow LED anode│ cathode → GND
  RPi GPIO 22 ──[330Ω]──► Green LED anode │ cathode → GND
  RPi GPIO 18 ──────────► Button pin 1    │ pin 2   → GND
"""

import RPi.GPIO as GPIO
import time
import threading

# ---------------------------------------------------------------------------
# GPIO pin assignments — change these to match your physical wiring
# ---------------------------------------------------------------------------
PIN_RED    = 17
PIN_YELLOW = 27
PIN_GREEN  = 22
PIN_BUTTON = 18

# ---------------------------------------------------------------------------
# Timing constants (seconds)
# ---------------------------------------------------------------------------
DURATION_RED    = 5    # Normal red phase duration
DURATION_GREEN  = 5    # Normal green phase duration
DURATION_YELLOW = 2    # Normal yellow phase duration
DURATION_WALK   = 10   # How long red holds during a crosswalk event

DEBOUNCE_MS     = 300  # Button debounce time in milliseconds

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
# This flag is set by the button ISR and read by the main loop.
# Using a threading.Event makes it thread-safe.
crosswalk_requested = threading.Event()


# ---------------------------------------------------------------------------
# GPIO setup
# ---------------------------------------------------------------------------
def setup():
    """Initialise GPIO pins for output (LEDs) and input (button)."""
    GPIO.setmode(GPIO.BCM)          # Use Broadcom GPIO numbering
    GPIO.setwarnings(False)

    # LED pins as outputs, initially off (LOW)
    GPIO.setup(PIN_RED,    GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_YELLOW, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PIN_GREEN,  GPIO.OUT, initial=GPIO.LOW)

    # Button pin as input with internal pull-up resistor.
    # Button press pulls the pin LOW (active-low logic).
    GPIO.setup(PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Attach interrupt — fires on falling edge (press), debounced in hardware
    GPIO.add_event_detect(
        PIN_BUTTON,
        GPIO.FALLING,
        callback=button_callback,
        bouncetime=DEBOUNCE_MS
    )

    print("GPIO initialised.")


# ---------------------------------------------------------------------------
# Button callback (runs in a separate thread triggered by the interrupt)
# ---------------------------------------------------------------------------
def button_callback(channel):
    """
    Called automatically when the button is pressed.
    Sets the crosswalk flag; the main loop checks this after each phase.
    """
    if not crosswalk_requested.is_set():
        print("[Button] Crosswalk requested — will activate after current phase.")
        crosswalk_requested.set()


# ---------------------------------------------------------------------------
# LED helpers
# ---------------------------------------------------------------------------
def all_off():
    """Turn all three LEDs off."""
    GPIO.output(PIN_RED,    GPIO.LOW)
    GPIO.output(PIN_YELLOW, GPIO.LOW)
    GPIO.output(PIN_GREEN,  GPIO.LOW)


def set_light(red=False, yellow=False, green=False):
    """Set each LED to the requested state (True = on, False = off)."""
    GPIO.output(PIN_RED,    GPIO.HIGH if red    else GPIO.LOW)
    GPIO.output(PIN_YELLOW, GPIO.HIGH if yellow else GPIO.LOW)
    GPIO.output(PIN_GREEN,  GPIO.HIGH if green  else GPIO.LOW)


# ---------------------------------------------------------------------------
# Traffic light phases
# ---------------------------------------------------------------------------
def phase_red(duration=DURATION_RED):
    """Illuminate red LED for the given duration."""
    print(f"[Light] RED  ({duration}s)")
    set_light(red=True)
    time.sleep(duration)
    all_off()


def phase_green():
    """Illuminate green LED for the standard green duration."""
    print(f"[Light] GREEN ({DURATION_GREEN}s)")
    set_light(green=True)
    time.sleep(DURATION_GREEN)
    all_off()


def phase_yellow():
    """Illuminate yellow LED for the standard yellow duration."""
    print(f"[Light] YELLOW ({DURATION_YELLOW}s)")
    set_light(yellow=True)
    time.sleep(DURATION_YELLOW)
    all_off()


# ---------------------------------------------------------------------------
# Crosswalk sequence
# ---------------------------------------------------------------------------
def crosswalk_sequence():
    """
    Extended red phase to allow pedestrians to cross safely.
    Holds red for DURATION_WALK seconds, then clears the request flag
    so normal cycling can resume.
    """
    print("[Crosswalk] WALK signal active — holding RED.")
    phase_red(duration=DURATION_WALK)
    crosswalk_requested.clear()
    print("[Crosswalk] Complete — resuming normal cycle.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    """
    Run the traffic light indefinitely.

    Each iteration runs one full normal cycle (red → green → yellow).
    After each phase completes, the loop checks whether a crosswalk was
    requested. If so, it runs the crosswalk sequence before continuing.
    """
    print("Traffic light controller started. Press Ctrl+C to exit.\n")

    while True:
        # --- Red phase ---
        phase_red()
        if crosswalk_requested.is_set():
            crosswalk_sequence()
            continue  # Restart cycle from red after crosswalk

        # --- Green phase ---
        phase_green()
        if crosswalk_requested.is_set():
            # Must show yellow before switching to crosswalk red
            phase_yellow()
            crosswalk_sequence()
            continue

        # --- Yellow phase ---
        phase_yellow()
        if crosswalk_requested.is_set():
            crosswalk_sequence()
            continue


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    setup()
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down — cleaning up GPIO.")
    finally:
        # Always clean up GPIO to avoid warnings on next run
        all_off()
        GPIO.cleanup()
        print("GPIO cleaned up. Goodbye.")