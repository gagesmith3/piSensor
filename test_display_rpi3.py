#!/usr/bin/env python3
"""
Waveshare 1.3" OLED HAT Display Test for Raspberry Pi 3 Model B v1.2
- Assumes 4-wire SPI mode (default for HAT)
- Uses BCM pin numbering
- Tests display and button/joystick input
"""

import time
import sys
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    from PIL import ImageFont
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("\nPlease install required packages:")
    print("  pip install luma.oled pillow RPi.GPIO spidev")
    sys.exit(1)

# GPIO pin definitions (BCM)
KEY1_PIN = 21
KEY2_PIN = 20
KEY3_PIN = 16
JOYSTICK_UP = 6
JOYSTICK_DOWN = 19
JOYSTICK_LEFT = 5
JOYSTICK_RIGHT = 26
JOYSTICK_PRESS = 13

# SPI pins (BCM)
SPI_MOSI = 10
SPI_CLK = 11
SPI_CS = 8
DC_PIN = 24
RST_PIN = 25

class DisplayTest:
    def __init__(self):
        print("Initializing display (SH1106, 4-wire SPI)...")
        try:
            serial = spi(device=0, port=0, bus_speed_hz=8000000, dc_pin=DC_PIN, rst_pin=RST_PIN)
            self.device = sh1106(serial, rotate=2)
            print(f"✓ Display initialized: {self.device.width}x{self.device.height}")
        except Exception as e:
            print(f"✗ Display init failed: {e}")
            sys.exit(1)
        try:
            self.font = ImageFont.load_default()
        except:
            self.font = None
        self.setup_buttons()
        self.button_presses = {k: 0 for k in ['KEY1','KEY2','KEY3','UP','DOWN','LEFT','RIGHT','PRESS']}
        self.last_button = "None"
        self.current_screen = 0
        self.test_counter = 0
    def setup_buttons(self):
        GPIO.setmode(GPIO.BCM)
        pins = [KEY1_PIN, KEY2_PIN, KEY3_PIN, JOYSTICK_UP, JOYSTICK_DOWN, JOYSTICK_LEFT, JOYSTICK_RIGHT, JOYSTICK_PRESS]
        for pin in pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pin, GPIO.FALLING, callback=self.button_callback, bouncetime=200)
            except Exception as e:
                print(f"GPIO {pin} setup failed: {e}")
    def button_callback(self, channel):
        pin_map = {
            KEY1_PIN: 'KEY1', KEY2_PIN: 'KEY2', KEY3_PIN: 'KEY3',
            JOYSTICK_UP: 'UP', JOYSTICK_DOWN: 'DOWN', JOYSTICK_LEFT: 'LEFT',
            JOYSTICK_RIGHT: 'RIGHT', JOYSTICK_PRESS: 'PRESS'
        }
        btn = pin_map.get(channel, str(channel))
        self.button_presses[btn] += 1
        self.last_button = btn
        if btn == 'LEFT':
            self.current_screen = (self.current_screen - 1) % 4
        elif btn == 'RIGHT':
            self.current_screen = (self.current_screen + 1) % 4
        elif btn == 'UP':
            self.test_counter += 1
        elif btn == 'DOWN':
            self.test_counter = max(0, self.test_counter - 1)
        elif btn == 'PRESS':
            self.test_counter = 0
        print(f"Button: {btn} (Total: {self.button_presses[btn]})")
    def clear_display(self):
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
    def draw_screen_0(self):
        with canvas(self.device) as draw:
            draw.text((10, 0), "WAVESHARE HAT", font=self.font, fill="white")
            draw.text((25, 20), "RPI 3B v1.2", font=self.font, fill="white")
            draw.text((5, 35), "128x64 OLED", font=self.font, fill="white")
            draw.text((0, 50), "Use <- -> to navigate", font=self.font, fill="white")
    def draw_screen_1(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "=== SYSTEM INFO ===", font=self.font, fill="white")
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                ip = "N/A"
            draw.text((0, 15), f"IP: {ip}", font=self.font, fill="white")
            draw.text((0, 28), f"Time: {datetime.now().strftime('%H:%M:%S')}", font=self.font, fill="white")
            draw.text((0, 41), f"Counter: {self.test_counter}", font=self.font, fill="white")
            draw.text((0, 54), f"Screen: {self.current_screen + 1}/4", font=self.font, fill="white")
    def draw_screen_2(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "=== BUTTON TEST ===", font=self.font, fill="white")
            draw.text((0, 12), f"Last: {self.last_button}", font=self.font, fill="white")
            y = 25
            for btn in ['KEY1', 'KEY2', 'KEY3']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font, fill="white")
                y += 12
    def draw_screen_3(self):
        with canvas(self.device) as draw:
            draw.text((0, 0), "== JOYSTICK TEST ==", font=self.font, fill="white")
            y = 12
            for btn in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'PRESS']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font, fill="white")
                y += 10
    def run_test(self):
        print("\nDisplay Test Running (RPI 3B v1.2)")
        print("Controls: LEFT/RIGHT to change screen, UP/DOWN to change counter, PRESS to reset, KEY1/2/3 to test buttons, Ctrl+C to exit")
        try:
            print("Testing display patterns...")
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="white", fill="white")
            time.sleep(0.5)
            self.clear_display()
            time.sleep(0.5)
            with canvas(self.device) as draw:
                for x in range(0, 128, 8):
                    for y in range(0, 64, 8):
                        if (x + y) % 16 == 0:
                            draw.rectangle((x, y, x+8, y+8), fill="white")
            time.sleep(0.5)
            print("✓ Display pattern test complete. You should see content now!")
            frame_count = 0
            while True:
                if self.current_screen == 0:
                    self.draw_screen_0()
                elif self.current_screen == 1:
                    self.draw_screen_1()
                elif self.current_screen == 2:
                    self.draw_screen_2()
                elif self.current_screen == 3:
                    self.draw_screen_3()
                frame_count += 1
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nTest stopped by user")
            self.cleanup()
    def cleanup(self):
        print("Cleaning up...")
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            draw.text((20, 25), "Test Complete", font=self.font, fill="white")
        time.sleep(1)
        self.clear_display()
        GPIO.cleanup()
        print("✓ Cleanup complete")
def main():
    print("\nWaveshare 1.3\" OLED HAT Test (RPI 3B v1.2)")
    try:
        test = DisplayTest()
        test.run_test()
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            GPIO.cleanup()
        except:
            pass
if __name__ == "__main__":
    main()
