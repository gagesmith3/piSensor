#!/usr/bin/env python3
"""
Brightness and Visibility Test for Waveshare OLED
Tests if display is working but just very dim
"""

import time
import sys

try:
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
except ImportError as e:
    print(f"Error: {e}")
    sys.exit(1)

def test_brightness():
    """Test display with maximum brightness patterns"""
    print("Initializing display with SH1106, rotation=0...")
    
    serial = spi(device=0, port=0, bus_speed_hz=8000000, transfer_size=4096)
    device = sh1106(serial, rotate=0)
    
    print("✓ Display initialized")
    print(f"  Size: {device.width}x{device.height}")
    print(f"  Mode: {device.mode}")
    
    print("\nRunning visibility tests...")
    print("Look at the display for changes every 2 seconds\n")
    
    # Test 1: Full white screen (easiest to see)
    print("1. FULL WHITE SCREEN (2 seconds)")
    print("   → Should see completely bright white display")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="white")
    time.sleep(2)
    
    # Test 2: Full black screen
    print("2. FULL BLACK SCREEN (2 seconds)")
    print("   → Display should go completely dark")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
    time.sleep(2)
    
    # Test 3: White screen again
    print("3. FULL WHITE SCREEN AGAIN (2 seconds)")
    print("   → Should see bright white again")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="white")
    time.sleep(2)
    
    # Test 4: Large text
    print("4. LARGE TEXT (2 seconds)")
    print("   → Should see 'TEST' in large letters")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        # Draw very large pixels manually for "TEST"
        for y in range(20, 45):
            for x in range(10, 118):
                if x % 2 == 0:  # Checkerboard pattern
                    draw.point((x, y), fill="white")
    time.sleep(2)
    
    # Test 5: Blinking pattern
    print("5. BLINKING PATTERN (5 blinks)")
    print("   → Display should blink on/off 5 times")
    for i in range(5):
        # White
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="white")
        time.sleep(0.5)
        
        # Black
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="black", fill="black")
        time.sleep(0.5)
    
    # Test 6: Border test
    print("6. BORDER TEST (2 seconds)")
    print("   → Should see white border around edges")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        # Draw thick border
        for i in range(5):
            draw.rectangle((i, i, device.width-1-i, device.height-1-i), outline="white")
    time.sleep(2)
    
    # Test 7: Vertical lines
    print("7. VERTICAL LINES (2 seconds)")
    print("   → Should see alternating vertical white lines")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        for x in range(0, device.width, 4):
            draw.line((x, 0, x, device.height), fill="white")
    time.sleep(2)
    
    # Test 8: Horizontal lines
    print("8. HORIZONTAL LINES (2 seconds)")
    print("   → Should see alternating horizontal white lines")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
        for y in range(0, device.height, 4):
            draw.line((0, y, device.width, y), fill="white")
    time.sleep(2)
    
    # Final: Clear
    print("9. CLEARING DISPLAY")
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)
    print("\nDid you see ANY changes on the display?")
    print("  YES → Display is working, might be contrast/visibility issue")
    print("  NO  → Check:")
    print("         - HAT firmly seated on GPIO pins")
    print("         - Display power (should have backlight)")
    print("         - Try rotation=2 instead")

if __name__ == "__main__":
    print("="*60)
    print("Display Brightness and Visibility Test")
    print("="*60)
    print("\nThis will test if the display is working")
    print("Watch the physical display for changes\n")
    
    try:
        test_brightness()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
