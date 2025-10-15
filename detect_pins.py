#!/usr/bin/env python3
"""
GPIO Pin Detection Helper for Waveshare OLED HAT
Helps identify which pins are available and which are in use
"""

import RPi.GPIO as GPIO
import time

# Waveshare 1.3" OLED HAT common pin configurations
# Different HAT revisions may use different pins

CONFIG_A = {
    "name": "Standard Waveshare 1.3\" v2",
    "pins": {
        "KEY1": 21,
        "KEY2": 20,
        "KEY3": 16,
        "UP": 6,
        "DOWN": 19,
        "LEFT": 5,
        "RIGHT": 26,
        "CENTER": 13
    }
}

CONFIG_B = {
    "name": "Waveshare 1.3\" v1 (alternate)",
    "pins": {
        "KEY1": 21,
        "KEY2": 20,
        "KEY3": 16,
        "UP": 6,
        "DOWN": 19,
        "LEFT": 5,
        "RIGHT": 26,
        "CENTER": 13
    }
}

# SPI pins used by display (DO NOT USE FOR BUTTONS)
SPI_PINS = {
    7: "SPI0_CE1",
    8: "SPI0_CE0",
    9: "SPI0_MISO",
    10: "SPI0_MOSI",
    11: "SPI0_SCLK",
    24: "DC (Data/Command)",
    25: "RST (Reset)"
}

def test_pin(pin_number, pin_name):
    """Test if a pin can be used for input with edge detection"""
    try:
        # Setup pin
        GPIO.setup(pin_number, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Try to add edge detection
        GPIO.add_event_detect(pin_number, GPIO.BOTH, bouncetime=100)
        
        # If we got here, it works
        GPIO.remove_event_detect(pin_number)
        GPIO.cleanup(pin_number)
        
        return True, "Available"
        
    except RuntimeError as e:
        return False, f"Runtime Error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def scan_pins():
    """Scan all GPIO pins to find available ones"""
    print("="*60)
    print("GPIO Pin Scanner for Waveshare OLED HAT")
    print("="*60)
    print()
    
    GPIO.setmode(GPIO.BCM)
    
    # Test each configuration
    for config in [CONFIG_A, CONFIG_B]:
        print(f"\nTesting: {config['name']}")
        print("-" * 60)
        
        results = {}
        for name, pin in config['pins'].items():
            # Skip SPI pins
            if pin in SPI_PINS:
                results[name] = (pin, False, f"Reserved for {SPI_PINS[pin]}")
                continue
            
            success, message = test_pin(pin, name)
            results[name] = (pin, success, message)
            
            status = "✓" if success else "✗"
            print(f"{status} {name:12} GPIO {pin:2d}  - {message}")
        
        # Summary
        working = sum(1 for _, success, _ in results.values() if success)
        total = len(results)
        print(f"\nWorking pins: {working}/{total}")
        
        if working >= 5:  # At least joystick should work
            print(f"✓ This configuration should work!")
        
    # Additional diagnostics
    print("\n" + "="*60)
    print("SPI Pins (Used by Display - DO NOT USE):")
    print("-" * 60)
    for pin, function in SPI_PINS.items():
        print(f"  GPIO {pin:2d}: {function}")
    
    print("\n" + "="*60)
    print("Recommendations:")
    print("-" * 60)
    print("1. Only use pins that show ✓ (Available)")
    print("2. Avoid SPI pins (7-11, 24-25) completely")
    print("3. If no pins work, check:")
    print("   - HAT is properly seated on GPIO header")
    print("   - No other programs using GPIO")
    print("   - Run: sudo lsof /dev/gpiomem")
    print("4. Try running with: sudo python3 detect_pins.py")
    
    GPIO.cleanup()

def show_current_config():
    """Show the pin configuration currently used in test_display.py"""
    print("\n" + "="*60)
    print("Current test_display.py Configuration:")
    print("-" * 60)
    
    current_config = {
        "KEY1": 21,
        "KEY2": 20,
        "KEY3": 16,
        "UP": 6,
        "DOWN": 19,
        "LEFT": 5,
        "RIGHT": 26,
        "CENTER": 13
    }
    
    for name, pin in current_config.items():
        reserved = " (SPI - CONFLICT!)" if pin in SPI_PINS else ""
        print(f"  {name:12} = GPIO {pin:2d}{reserved}")

if __name__ == "__main__":
    print()
    show_current_config()
    print()
    
    try:
        scan_pins()
    except KeyboardInterrupt:
        print("\n\nScan interrupted")
        GPIO.cleanup()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        GPIO.cleanup()
    
    print("\n" + "="*60)
    print()
