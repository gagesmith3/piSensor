#!/usr/bin/env python3
"""
Waveshare 1.3" OLED Display HAT Test Script - Polling Version
Uses GPIO polling instead of interrupts to avoid permission issues
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
KEY1_PIN = 21  # Button 1
KEY2_PIN = 20  # Button 2
KEY3_PIN = 16  # Button 3

JOYSTICK_UP = 6
JOYSTICK_DOWN = 19
JOYSTICK_LEFT = 5
JOYSTICK_RIGHT = 26
JOYSTICK_PRESS = 13

class DisplayTest:
    def __init__(self):
        """Initialize the display and GPIO"""
        print("Initializing Waveshare 1.3\" OLED HAT (Polling Mode)...")
        
        # Initialize SPI display
        try:
            serial = spi(device=0, port=0, bus_speed_hz=8000000, transfer_size=4096)
            self.device = sh1106(serial, rotate=2)
            print("✓ Display initialized successfully")
        except Exception as e:
            print(f"✗ Failed to initialize display: {e}")
            sys.exit(1)
        
        # Load fonts
        try:
            self.font = ImageFont.load_default()
            self.font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
            self.font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
        except:
            print("⚠ Using default font")
            self.font = ImageFont.load_default()
            self.font_large = self.font
            self.font_small = self.font
        
        # Setup GPIO for buttons (polling mode - no interrupts)
        self.setup_buttons()
        
        # Test state
        self.current_screen = 0
        self.button_presses = {
            'KEY1': 0, 'KEY2': 0, 'KEY3': 0,
            'UP': 0, 'DOWN': 0, 'LEFT': 0, 'RIGHT': 0, 'PRESS': 0
        }
        self.last_button = "None"
        self.test_counter = 0
        
        # Button state tracking for edge detection
        self.button_states = {}
        self.pins = {
            KEY1_PIN: 'KEY1',
            KEY2_PIN: 'KEY2',
            KEY3_PIN: 'KEY3',
            JOYSTICK_UP: 'UP',
            JOYSTICK_DOWN: 'DOWN',
            JOYSTICK_LEFT: 'LEFT',
            JOYSTICK_RIGHT: 'RIGHT',
            JOYSTICK_PRESS: 'PRESS'
        }
        
        # Initialize button states
        for pin in self.pins.keys():
            self.button_states[pin] = GPIO.input(pin)
    
    def setup_buttons(self):
        """Setup GPIO pins for buttons and joystick - polling mode only"""
        GPIO.setmode(GPIO.BCM)
        
        pins = [KEY1_PIN, KEY2_PIN, KEY3_PIN, JOYSTICK_UP, JOYSTICK_DOWN, 
                JOYSTICK_LEFT, JOYSTICK_RIGHT, JOYSTICK_PRESS]
        
        successful_pins = 0
        for pin in pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                print(f"✓ GPIO {pin} configured for polling")
                successful_pins += 1
            except Exception as e:
                print(f"✗ Failed to setup GPIO {pin}: {e}")
        
        if successful_pins > 0:
            print(f"✓ {successful_pins}/{len(pins)} pins configured successfully")
            print("✓ Using polling mode (no interrupts needed)")
        else:
            print("✗ No pins could be configured!")
            sys.exit(1)
    
    def poll_buttons(self):
        """Poll button states and detect changes (manual edge detection)"""
        for pin, name in self.pins.items():
            try:
                current_state = GPIO.input(pin)
                previous_state = self.button_states[pin]
                
                # Detect falling edge (button press)
                if previous_state == 1 and current_state == 0:
                    self.button_callback(name)
                
                self.button_states[pin] = current_state
            except Exception as e:
                pass  # Ignore errors on individual pin reads
    
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
            draw.text((20, 35), "POLLING MODE", font=self.font_small, fill="white")
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
    
    def run_test(self):
        """Run the display test loop"""
        print("\n" + "="*50)
        print("Display Test Running (Polling Mode)")
        print("="*50)
        print("\nControls:")
        print("  LEFT/RIGHT  - Navigate screens")
        print("  UP/DOWN     - Increment/Decrement counter")
        print("  CENTER      - Reset counter")
        print("  KEY1/2/3    - Test buttons")
        print("  Ctrl+C      - Exit test")
        print("\nNote: Using polling mode - no sudo required!")
        print("="*50 + "\n")
        
        try:
            # Initial display test
            print("Testing display patterns...")
            
            # White screen
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, outline="white", fill="white")
            time.sleep(0.5)
            
            # Black screen
            self.clear_display()
            time.sleep(0.5)
            
            # Checkerboard
            with canvas(self.device) as draw:
                for x in range(0, 128, 8):
                    for y in range(0, 64, 8):
                        if (x + y) % 16 == 0:
                            draw.rectangle((x, y, x+8, y+8), fill="white")
            time.sleep(0.5)
            
            print("✓ Display pattern test complete\n")
            
            # Main loop
            frame_count = 0
            last_poll = time.time()
            
            while True:
                # Poll buttons at 50Hz (every 20ms)
                current_time = time.time()
                if current_time - last_poll >= 0.02:
                    self.poll_buttons()
                    last_poll = current_time
                
                # Update display at 10Hz (every 100ms)
                if frame_count % 5 == 0:
                    if self.current_screen == 0:
                        self.draw_screen_0()
                    elif self.current_screen == 1:
                        self.draw_screen_1()
                    elif self.current_screen == 2:
                        self.draw_screen_2()
                    elif self.current_screen == 3:
                        self.draw_screen_3()
                
                frame_count += 1
                time.sleep(0.02)  # 50Hz main loop
                
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
    print("  Polling Mode - No sudo required")
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
