#!/usr/bin/env python3
"""
Waveshare 1.3" OLED HAT Display Test with Boot Animation
For Raspberry Pi 3 Model B v1.2
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

DC_PIN = 24
RST_PIN = 25

class BootAnimation:
    """Cool boot animation for the display"""
    
    def __init__(self, device, font):
        self.device = device
        self.font = font
    
    def draw_logo_frame(self, progress):
        """Draw a single frame of the logo animation"""
        with canvas(self.device) as draw:
            # Draw a cool expanding circle logo
            center_x = 64
            center_y = 32
            max_radius = 30
            
            # Expanding circles
            radius = int(max_radius * progress)
            if radius > 0:
                draw.ellipse((center_x - radius, center_y - radius,
                             center_x + radius, center_y + radius),
                            outline="white", fill=None)
            
            # Inner circle appears halfway through
            if progress > 0.5:
                inner_radius = int(radius * 0.6)
                draw.ellipse((center_x - inner_radius, center_y - inner_radius,
                             center_x + inner_radius, center_y + inner_radius),
                            outline="white", fill="white")
            
            # Draw "Pi Sensor" text that fades in
            if progress > 0.7:
                text_alpha = (progress - 0.7) / 0.3  # 0 to 1
                if text_alpha > 0.5:
                    draw.text((20, 5), "Pi Sensor", font=self.font, fill="white")
                    draw.text((30, 50), "v2.0", font=self.font, fill="white")
    
    def expanding_box_animation(self):
        """Expanding box with text reveal"""
        for i in range(20):
            progress = i / 19.0
            with canvas(self.device) as draw:
                # Expanding box from center
                width = int(128 * progress)
                height = int(64 * progress)
                x = (128 - width) // 2
                y = (64 - height) // 2
                
                draw.rectangle((x, y, x + width, y + height), outline="white")
                
                # Text appears when box is 80% expanded
                if progress > 0.8:
                    draw.text((15, 25), "WAVESHARE", font=self.font, fill="white")
            time.sleep(0.03)
    
    def loading_bar_animation(self):
        """Classic loading bar"""
        with canvas(self.device) as draw:
            draw.text((25, 10), "INITIALIZING", font=self.font, fill="white")
        
        time.sleep(0.3)
        
        for i in range(101):
            progress = i / 100.0
            with canvas(self.device) as draw:
                draw.text((25, 10), "INITIALIZING", font=self.font, fill="white")
                
                # Loading bar
                bar_width = 100
                bar_height = 10
                bar_x = (128 - bar_width) // 2
                bar_y = 35
                
                # Outer border
                draw.rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
                              outline="white")
                
                # Filled portion
                fill_width = int(bar_width * progress) - 2
                if fill_width > 0:
                    draw.rectangle((bar_x + 1, bar_y + 1,
                                  bar_x + 1 + fill_width, bar_y + bar_height - 1),
                                  fill="white")
                
                # Percentage
                draw.text((50, 50), f"{i}%", font=self.font, fill="white")
            
            time.sleep(0.02)
    
    def pixel_rain_animation(self):
        """Matrix-style pixel rain"""
        import random
        
        # Initialize columns
        columns = []
        for x in range(0, 128, 4):
            columns.append({
                'x': x,
                'y': random.randint(-64, 0),
                'speed': random.randint(2, 6)
            })
        
        for frame in range(40):
            with canvas(self.device) as draw:
                # Update and draw each column
                for col in columns:
                    # Draw trail
                    for i in range(8):
                        y = col['y'] - (i * 4)
                        if 0 <= y < 64:
                            brightness = 8 - i
                            if brightness > 4:
                                draw.point((col['x'], y), fill="white")
                    
                    # Move column down
                    col['y'] += col['speed']
                    
                    # Reset if off screen
                    if col['y'] > 64:
                        col['y'] = random.randint(-32, 0)
                        col['speed'] = random.randint(2, 6)
                
                # Draw "READY" text in center after halfway
                if frame > 20:
                    draw.text((40, 25), "READY", font=self.font, fill="white")
            
            time.sleep(0.05)
    
    def run_full_boot_sequence(self):
        """Run the complete boot animation sequence"""
        print("Running boot animation...")
        
        # 1. Logo animation
        print("  - Logo animation")
        for i in range(30):
            progress = i / 29.0
            self.draw_logo_frame(progress)
            time.sleep(0.03)
        
        time.sleep(0.3)
        
        # 2. Loading bar
        print("  - Loading sequence")
        self.loading_bar_animation()
        
        time.sleep(0.2)
        
        # 3. Pixel rain
        print("  - Pixel rain effect")
        self.pixel_rain_animation()
        
        # 4. Final "READY" message
        with canvas(self.device) as draw:
            draw.text((35, 20), "SYSTEM", font=self.font, fill="white")
            draw.text((40, 35), "READY", font=self.font, fill="white")
        
        time.sleep(1)
        
        print("✓ Boot animation complete!")

class DisplayTest:
    def __init__(self):
        # Initialize GPIO FIRST
        print("Setting up GPIO (polling mode - no interrupts)...")
        self.setup_buttons()
        
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
        
        # Run boot animation
        boot_anim = BootAnimation(self.device, self.font)
        boot_anim.run_full_boot_sequence()
        
        self.button_presses = {k: 0 for k in ['KEY1','KEY2','KEY3','UP','DOWN','LEFT','RIGHT','PRESS']}
        self.last_button = "None"
        self.current_screen = 0
        self.test_counter = 0
        
        # Button state tracking for polling
        self.button_states = {}
        self.pin_map = {
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
        for pin in self.pin_map.keys():
            try:
                self.button_states[pin] = GPIO.input(pin)
            except:
                self.button_states[pin] = 1
    
    def setup_buttons(self):
        GPIO.setmode(GPIO.BCM)
        print("✓ GPIO mode set to BCM")
        
        pins = [KEY1_PIN, KEY2_PIN, KEY3_PIN, JOYSTICK_UP, JOYSTICK_DOWN, 
                JOYSTICK_LEFT, JOYSTICK_RIGHT, JOYSTICK_PRESS]
        
        for pin in pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                print(f"✓ GPIO {pin} configured")
            except Exception as e:
                print(f"✗ GPIO {pin} setup failed: {e}")
        
        print("✓ All buttons configured for POLLING")
    
    def poll_buttons(self):
        for pin, name in self.pin_map.items():
            try:
                current_state = GPIO.input(pin)
                previous_state = self.button_states.get(pin, 1)
                
                if previous_state == 1 and current_state == 0:
                    self.handle_button_press(name)
                
                self.button_states[pin] = current_state
            except:
                pass
    
    def handle_button_press(self, btn):
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
            draw.text((15, 15), "POLLING MODE", font=self.font, fill="white")
            draw.text((5, 30), "128x64 OLED", font=self.font, fill="white")
            draw.text((0, 45), "Use <- -> navigate", font=self.font, fill="white")
    
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
        print("\n" + "="*60)
        print("Display Test Running (RPI 3B - POLLING MODE)")
        print("="*60)
        print("\nControls:")
        print("  LEFT/RIGHT  - Navigate screens")
        print("  UP/DOWN     - Increment/Decrement counter")
        print("  PRESS       - Reset counter")
        print("  KEY1/2/3    - Test buttons")
        print("  Ctrl+C      - Exit test")
        print("\n" + "="*60 + "\n")
        
        try:
            frame_count = 0
            last_poll = time.time()
            last_display_update = time.time()
            
            while True:
                current_time = time.time()
                
                if current_time - last_poll >= 0.02:
                    self.poll_buttons()
                    last_poll = current_time
                
                if current_time - last_display_update >= 0.1:
                    if self.current_screen == 0:
                        self.draw_screen_0()
                    elif self.current_screen == 1:
                        self.draw_screen_1()
                    elif self.current_screen == 2:
                        self.draw_screen_2()
                    elif self.current_screen == 3:
                        self.draw_screen_3()
                    
                    last_display_update = current_time
                
                time.sleep(0.005)
                
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
    print("\n" + "="*60)
    print("  Waveshare 1.3\" OLED HAT Test with Boot Animation")
    print("  Raspberry Pi 3 Model B v1.2")
    print("="*60 + "\n")
    
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
