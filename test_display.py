#!/usr/bin/env python3
"""
Waveshare 1.3" OLED Display HAT Test Script
Tests display functionality and button/joystick inputs
No sensor required - display and input testing only
"""

import time
import sys
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    from PIL import ImageFont, ImageDraw
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("\nPlease install required packages:")
    print("  pip install luma.oled pillow RPi.GPIO")
    sys.exit(1)

# Waveshare 1.3" OLED HAT GPIO Pin Definitions
# Based on official Waveshare documentation for SH1106 1.3" HAT
# SPI Display uses: GPIO 8(DC), 25(RST), 7,8,9,10,11(SPI)
# Available for buttons/joystick:

KEY1_PIN = 21  # Physical pin 40
KEY2_PIN = 20  # Physical pin 38
KEY3_PIN = 16  # Physical pin 36

JOYSTICK_UP = 6     # Physical pin 31
JOYSTICK_DOWN = 19  # Physical pin 35
JOYSTICK_LEFT = 5   # Physical pin 29
JOYSTICK_RIGHT = 26 # Physical pin 37
JOYSTICK_PRESS = 13 # Physical pin 33

class DisplayTest:
    def __init__(self):
        """Initialize the display and GPIO"""
        print("Initializing Waveshare 1.3\" OLED HAT...")
        
        # Initialize SPI display (SH1106 controller for 1.3" HAT)
        try:
            serial = spi(device=0, port=0, bus_speed_hz=8000000, transfer_size=4096)
            self.device = sh1106(serial, rotate=2)  # rotate=2 for correct orientation
            print("✓ Display initialized successfully")
        except Exception as e:
            print(f"✗ Failed to initialize display: {e}")
            print("\nMake sure:")
            print("  1. SPI is enabled: sudo raspi-config -> Interface Options -> SPI")
            print("  2. HAT is properly connected to GPIO pins")
            sys.exit(1)
        
        # Load font
        try:
            self.font = ImageFont.load_default()
            self.font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
            self.font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
        except:
            print("⚠ Using default font (custom fonts not available)")
            self.font = ImageFont.load_default()
            self.font_large = self.font
            self.font_small = self.font
        
        # Setup GPIO for buttons
        self.setup_buttons()
        
        # Test state
        self.current_screen = 0
        self.button_presses = {
            'KEY1': 0, 'KEY2': 0, 'KEY3': 0,
            'UP': 0, 'DOWN': 0, 'LEFT': 0, 'RIGHT': 0, 'PRESS': 0
        }
        self.last_button = "None"
        self.test_counter = 0
        
    def setup_buttons(self):
        """Setup GPIO pins for buttons and joystick"""
        GPIO.setmode(GPIO.BCM)
        
        # Waveshare HAT pin mapping - these are the standard pins for the 1.3" HAT
        # If these fail, you may need to adjust based on your specific HAT model
        pins = {
            KEY1_PIN: 'KEY1',
            KEY2_PIN: 'KEY2',
            KEY3_PIN: 'KEY3',
            JOYSTICK_UP: 'UP',
            JOYSTICK_DOWN: 'DOWN',
            JOYSTICK_LEFT: 'LEFT',
            JOYSTICK_RIGHT: 'RIGHT',
            JOYSTICK_PRESS: 'PRESS'
        }
        
        successful_pins = []
        failed_pins = []
        
        for pin, name in pins.items():
            try:
                # First try to setup the pin
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Then try to add event detection
                GPIO.add_event_detect(pin, GPIO.FALLING, 
                                    callback=lambda ch, n=name: self.button_callback(n),
                                    bouncetime=300)
                print(f"✓ {name} button configured on GPIO {pin}")
                successful_pins.append((pin, name))
                
            except RuntimeError as e:
                # Pin might be in use or conflicting
                print(f"⚠ Skipping {name} on GPIO {pin}: {e}")
                failed_pins.append((pin, name))
            except Exception as e:
                print(f"✗ Failed to setup {name} on GPIO {pin}: {e}")
                failed_pins.append((pin, name))
        
        if failed_pins:
            print(f"\n⚠ Warning: {len(failed_pins)} buttons failed to initialize")
            print("This is often normal - some pins may be used by the display SPI interface")
            print(f"Working buttons: {len(successful_pins)}/{len(pins)}")
        
        if not successful_pins:
            print("\n✗ No buttons could be configured!")
            print("The test will continue with display-only mode")
            print("\nTo find correct pin numbers, check:")
            print("  - Waveshare HAT documentation")
            print("  - Run: gpio readall")
            print("  - Check for pin conflicts with SPI (GPIO 7-11)")
        
        return len(successful_pins) > 0
    
    def button_callback(self, button_name):
        """Handle button press events"""
        self.button_presses[button_name] += 1
        self.last_button = button_name
        
        # Navigation
        if button_name == 'LEFT':
            self.current_screen = (self.current_screen - 1) % 4
        elif button_name == 'RIGHT':
            self.current_screen = (self.current_screen + 1) % 4
        elif button_name == 'UP':
            self.test_counter += 1
        elif button_name == 'DOWN':
            self.test_counter = max(0, self.test_counter - 1)
        elif button_name == 'PRESS':
            self.test_counter = 0
        
        print(f"Button pressed: {button_name} (Total: {self.button_presses[button_name]})")
    
    def clear_display(self):
        """Clear the display"""
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
    
    def draw_screen_0(self):
        """Welcome screen"""
        with canvas(self.device) as draw:
            draw.text((10, 0), "WAVESHARE HAT", font=self.font_large, fill="white")
            draw.text((15, 20), "Display Test", font=self.font_small, fill="white")
            draw.text((5, 35), "128x64 OLED", font=self.font_small, fill="white")
            draw.text((0, 50), "Use <- -> to navigate", font=self.font_small, fill="white")
    
    def draw_screen_1(self):
        """System info screen"""
        with canvas(self.device) as draw:
            draw.text((0, 0), "=== SYSTEM INFO ===", font=self.font_small, fill="white")
            
            # Get IP address
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                ip = "N/A"
            
            draw.text((0, 15), f"IP: {ip}", font=self.font_small, fill="white")
            draw.text((0, 28), f"Time: {datetime.now().strftime('%H:%M:%S')}", font=self.font_small, fill="white")
            draw.text((0, 41), f"Counter: {self.test_counter}", font=self.font_small, fill="white")
            draw.text((0, 54), f"Screen: {self.current_screen + 1}/4", font=self.font_small, fill="white")
    
    def draw_screen_2(self):
        """Button test screen"""
        with canvas(self.device) as draw:
            draw.text((0, 0), "=== BUTTON TEST ===", font=self.font_small, fill="white")
            draw.text((0, 12), f"Last: {self.last_button}", font=self.font_small, fill="white")
            
            y = 25
            for btn in ['KEY1', 'KEY2', 'KEY3']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font_small, fill="white")
                y += 12
    
    def draw_screen_3(self):
        """Joystick test screen"""
        with canvas(self.device) as draw:
            draw.text((0, 0), "== JOYSTICK TEST ==", font=self.font_small, fill="white")
            
            y = 12
            for btn in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'PRESS']:
                count = self.button_presses[btn]
                draw.text((0, y), f"{btn}: {count}", font=self.font_small, fill="white")
                y += 10
    
    def draw_graphics_test(self):
        """Draw some test graphics"""
        with canvas(self.device) as draw:
            # Border
            draw.rectangle(self.device.bounding_box, outline="white", fill="black")
            
            # Shapes
            draw.line((10, 10, 50, 30), fill="white")
            draw.rectangle((60, 10, 90, 30), outline="white", fill="black")
            draw.ellipse((10, 35, 40, 55), outline="white", fill="black")
            
            # Progress bar
            bar_width = int((self.test_counter % 100) * 1.2)
            draw.rectangle((5, 58, 5 + bar_width, 63), outline="white", fill="white")
    
    def run_test(self):
        """Run the display test loop"""
        print("\n" + "="*50)
        print("Display Test Running")
        print("="*50)
        print("\nControls:")
        print("  LEFT/RIGHT  - Navigate screens")
        print("  UP/DOWN     - Increment/Decrement counter")
        print("  CENTER      - Reset counter")
        print("  KEY1/2/3    - Test buttons")
        print("  Ctrl+C      - Exit test")
        print("\n" + "="*50 + "\n")
        
        try:
            # Initial display test - flash patterns
            print("Testing display patterns...")
            
            # White screen
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="white", fill="white")
            time.sleep(0.5)
            
            # Black screen
            self.clear_display()
            time.sleep(0.5)
            
            # Checkerboard pattern
            with canvas(self.device) as draw:
                for x in range(0, 128, 8):
                    for y in range(0, 64, 8):
                        if (x + y) % 16 == 0:
                            draw.rectangle((x, y, x+8, y+8), fill="white")
            time.sleep(0.5)
            
            print("✓ Display pattern test complete\n")
            
            # Main test loop
            frame_count = 0
            while True:
                # Draw current screen
                if self.current_screen == 0:
                    self.draw_screen_0()
                elif self.current_screen == 1:
                    self.draw_screen_1()
                elif self.current_screen == 2:
                    self.draw_screen_2()
                elif self.current_screen == 3:
                    self.draw_screen_3()
                
                frame_count += 1
                time.sleep(0.1)  # 10 FPS update rate
                
        except KeyboardInterrupt:
            print("\n\nTest stopped by user")
            self.cleanup()
    
    def cleanup(self):
        """Clean up GPIO and display"""
        print("\nCleaning up...")
        
        # Clear display
        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, outline="black", fill="black")
            draw.text((20, 25), "Test Complete", font=self.font_large, fill="white")
        
        time.sleep(1)
        self.clear_display()
        
        # Clean up GPIO
        GPIO.cleanup()
        print("✓ Cleanup complete")
        print("\nTest Summary:")
        print(f"  Button presses: {sum(self.button_presses.values())}")
        for btn, count in self.button_presses.items():
            if count > 0:
                print(f"    {btn}: {count}")

def main():
    """Main entry point"""
    print("\n" + "="*50)
    print("  Waveshare 1.3\" OLED Display HAT Test")
    print("="*50 + "\n")
    
    try:
        test = DisplayTest()
        test.run_test()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
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
