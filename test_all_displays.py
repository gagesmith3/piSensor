#!/usr/bin/env python3
"""
Test ALL possible Waveshare display configurations
Tries SPI, I2C, different devices, and rotations
"""

import time
import sys

try:
    from luma.core.interface.serial import spi, i2c
    from luma.core.render import canvas
    from luma.oled.device import sh1106, ssd1306, ssd1327, ssd1331
except ImportError as e:
    print(f"Error: {e}")
    sys.exit(1)

def test_config(interface_name, device_type, interface, rotation):
    """Test a specific configuration"""
    config_name = f"{interface_name} - {device_type.__name__} - rot{rotation}"
    
    try:
        device = device_type(interface, rotate=rotation)
        
        # Test 1: Full white
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, fill="white")
        
        print(f"✓ {config_name} - initialized")
        print(f"  Size: {device.width}x{device.height}")
        
        # If we got here, show a pattern
        time.sleep(1)
        
        # Test 2: Blinking
        for i in range(3):
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
            time.sleep(0.3)
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="white")
            time.sleep(0.3)
        
        # Clear
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, fill="black")
        
        return True, config_name
        
    except Exception as e:
        return False, f"{config_name}: {str(e)[:50]}"

def main():
    print("="*70)
    print("COMPREHENSIVE WAVESHARE DISPLAY TEST")
    print("="*70)
    print("\nTrying ALL possible configurations...")
    print("Watch your display for ANY blinking or white flashes!\n")
    
    results = []
    
    # SPI configurations
    print("\n--- Testing SPI Interface ---")
    try:
        spi_interface = spi(device=0, port=0, bus_speed_hz=8000000, transfer_size=4096)
        
        devices = [sh1106, ssd1306, ssd1327]
        rotations = [0, 2]
        
        for device_type in devices:
            for rotation in rotations:
                success, msg = test_config("SPI", device_type, spi_interface, rotation)
                results.append((success, msg))
                if success:
                    print(f"  ✓✓✓ FOUND WORKING CONFIG: {msg}")
                    print(f"       Did you see blinking on the display?")
                    time.sleep(2)
                else:
                    print(f"  ✗ {msg}")
                time.sleep(0.5)
                
    except Exception as e:
        print(f"  ✗ SPI not available: {e}")
        results.append((False, f"SPI Error: {e}"))
    
    # I2C configurations
    print("\n--- Testing I2C Interface ---")
    try:
        # Try different I2C addresses (Waveshare commonly uses 0x3C)
        for address in [0x3C, 0x3D]:
            try:
                i2c_interface = i2c(port=1, address=address)
                
                devices = [sh1106, ssd1306]
                rotations = [0, 2]
                
                for device_type in devices:
                    for rotation in rotations:
                        success, msg = test_config(f"I2C(0x{address:02X})", device_type, i2c_interface, rotation)
                        results.append((success, msg))
                        if success:
                            print(f"  ✓✓✓ FOUND WORKING CONFIG: {msg}")
                            print(f"       Did you see blinking on the display?")
                            time.sleep(2)
                        else:
                            print(f"  ✗ {msg}")
                        time.sleep(0.5)
                        
            except Exception as e:
                print(f"  ✗ I2C address 0x{address:02X} failed: {e}")
                
    except Exception as e:
        print(f"  ✗ I2C not available: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    successful = [r for r in results if r[0]]
    failed = [r for r in results if not r[0]]
    
    if successful:
        print(f"\n✓ WORKING configurations ({len(successful)}):")
        for _, config in successful:
            print(f"  ✓ {config}")
        print("\nDid you see ANY blinking or changes on the physical display?")
        print("If YES → Use one of the working configs above")
        print("If NO  → Hardware connection issue (see below)")
    else:
        print("\n✗ NO WORKING CONFIGURATIONS FOUND")
        print("\nPossible issues:")
        print("  1. HAT not properly seated on GPIO pins")
        print("  2. Wrong HAT model (not a Waveshare 1.3\" OLED)")
        print("  3. Defective display")
        print("  4. SPI/I2C not enabled in raspi-config")
        print("\nTroubleshooting steps:")
        print("  1. Remove and reseat the HAT firmly")
        print("  2. Run: sudo raspi-config")
        print("     → Interface Options → SPI → Enable")
        print("     → Interface Options → I2C → Enable")
        print("  3. Reboot: sudo reboot")
        print("  4. Check HAT documentation for jumper settings")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
