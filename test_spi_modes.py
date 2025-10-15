#!/usr/bin/env python3
"""
Test different SPI modes for Waveshare 1.3" OLED HAT
The HAT can be configured for 4-SPI, 3-SPI, or I2C via jumpers
"""

import time
import sys

try:
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
except ImportError as e:
    print(f"Error: {e}")
    print("Install with: pip install luma.oled")
    sys.exit(1)

def test_4wire_spi():
    """Test 4-wire SPI mode (most common for Waveshare HATs)"""
    print("\n" + "="*60)
    print("Testing 4-Wire SPI Mode")
    print("="*60)
    print("Jumper settings should be:")
    print("  BS1=0, BS0=0 (for 4-SPI mode)")
    print("  DC, CS, CLK, DIN connected")
    print()
    
    try:
        # Standard 4-wire SPI - DC pin is separate
        # CS is pin 8 (CE0), DC is pin 24
        serial = spi(device=0, port=0, bus_speed_hz=8000000, 
                    transfer_size=4096,
                    dc_pin=24,  # DC pin
                    rst_pin=25) # RST pin
        
        device = sh1106(serial, rotate=2)
        print(f"✓ Device initialized: {device.width}x{device.height}")
        
        # Test pattern
        print("Drawing test pattern (white screen)...")
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="white")
        time.sleep(1)
        
        # Text
        print("Drawing text...")
        with canvas(device) as draw:
            draw.text((10, 10), "4-WIRE SPI", fill="white")
            draw.text((10, 25), "SUCCESS!", fill="white")
        
        print("\n✓✓✓ 4-WIRE SPI WORKS! ✓✓✓")
        print("Look at your display - you should see white screen then text!")
        
        time.sleep(3)
        
        # Clear
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, fill="black")
        
        return True
        
    except Exception as e:
        print(f"✗ 4-wire SPI failed: {e}")
        return False

def test_3wire_spi():
    """Test 3-wire SPI mode"""
    print("\n" + "="*60)
    print("Testing 3-Wire SPI Mode")
    print("="*60)
    print("Jumper settings should be:")
    print("  BS1=0, BS0=1 (for 3-SPI mode)")
    print("  DC jumpered to 0, CS, CLK, DIN connected")
    print()
    
    try:
        # 3-wire SPI - no DC pin
        serial = spi(device=0, port=0, bus_speed_hz=8000000,
                    transfer_size=4096,
                    rst_pin=25)
        
        device = sh1106(serial, rotate=2)
        print(f"✓ Device initialized: {device.width}x{device.height}")
        
        # Test pattern
        print("Drawing test pattern (white screen)...")
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="white")
        time.sleep(1)
        
        # Text
        print("Drawing text...")
        with canvas(device) as draw:
            draw.text((10, 10), "3-WIRE SPI", fill="white")
            draw.text((10, 25), "SUCCESS!", fill="white")
        
        print("\n✓✓✓ 3-WIRE SPI WORKS! ✓✓✓")
        print("Look at your display - you should see white screen then text!")
        
        time.sleep(3)
        
        # Clear
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, fill="black")
        
        return True
        
    except Exception as e:
        print(f"✗ 3-wire SPI failed: {e}")
        return False

def test_simple_spi():
    """Test simplest SPI configuration (what we tried before)"""
    print("\n" + "="*60)
    print("Testing Simple SPI Mode (no DC/RST pins specified)")
    print("="*60)
    
    try:
        serial = spi(device=0, port=0, bus_speed_hz=8000000, transfer_size=4096)
        device = sh1106(serial, rotate=0)
        print(f"✓ Device initialized: {device.width}x{device.height}")
        
        # Aggressive visibility test
        print("Drawing BRIGHT WHITE screen...")
        for i in range(5):
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="white", fill="white")
            time.sleep(0.3)
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, outline="black", fill="black")
            time.sleep(0.3)
        
        print("Drawing large text...")
        with canvas(device) as draw:
            draw.text((10, 10), "SIMPLE SPI", fill="white")
            draw.text((10, 30), "TEST MODE", fill="white")
        
        print("\n✓✓✓ SIMPLE SPI WORKS! ✓✓✓")
        print("Look at your display - it should have blinked 5 times!")
        
        time.sleep(3)
        
        return True
        
    except Exception as e:
        print(f"✗ Simple SPI failed: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  Waveshare 1.3\" OLED HAT - SPI Mode Detection")
    print("="*60)
    print("\nThis will test all SPI configurations.")
    print("WATCH YOUR DISPLAY for blinking or text!")
    print()
    
    results = {
        "4-Wire SPI (with DC/RST pins)": False,
        "3-Wire SPI (no DC pin)": False,
        "Simple SPI (minimal config)": False
    }
    
    # Test all modes
    results["4-Wire SPI (with DC/RST pins)"] = test_4wire_spi()
    time.sleep(1)
    
    results["3-Wire SPI (no DC pin)"] = test_3wire_spi()
    time.sleep(1)
    
    results["Simple SPI (minimal config)"] = test_simple_spi()
    
    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    working_modes = []
    for mode, success in results.items():
        status = "✓ WORKS" if success else "✗ Failed"
        print(f"{mode:40s} {status}")
        if success:
            working_modes.append(mode)
    
    print("\n" + "="*60)
    if working_modes:
        print("✓✓✓ SUCCESS! Working mode(s):")
        for mode in working_modes:
            print(f"  - {mode}")
        print("\nDid you see anything on the display?")
    else:
        print("✗ No modes worked")
        print("\nPossible issues:")
        print("  1. Check HAT is firmly seated on GPIO pins")
        print("  2. Check jumper configuration on HAT")
        print("  3. Verify SPI is enabled: sudo raspi-config")
        print("  4. Check for protective film on display")
        print("  5. Try: ls -l /dev/spi* (should see spidev0.0)")
    print("="*60)

if __name__ == "__main__":
    main()
