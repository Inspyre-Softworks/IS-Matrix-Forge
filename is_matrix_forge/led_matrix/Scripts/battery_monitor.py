#!/usr/bin/env python
"""
Battery Monitor Script.

This script provides a command-line interface for monitoring the battery status
and displaying it on an LED matrix. It uses the PowerMonitor class from the
is_matrix_forge.monitor module to monitor the battery level and power state.

Usage:
    python battery_monitor.py [options]

Options:
    --interval SECONDS    Set the battery check interval in seconds (default: 5)
    --brightness PERCENT  Set the LED matrix brightness (0-100, default: 50)
    --device INDEX        Specify which LED matrix device to use (default: 0)
    --no-sound            Disable sound notifications
    --help                Show this help message and exit
"""

import argparse
import sys
from pathlib import Path

# Import the necessary modules from the is_matrix_forge package
from is_matrix_forge.monitor import run_power_monitor
from is_matrix_forge.led_matrix.helpers.device import get_devices
from is_matrix_forge.notify.sounds import Sound
from is_matrix_forge.led_matrix.led_matrix import LEDMatrix
from is_matrix_forge.led_matrix import initialize as init_led_matrix


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Monitor battery status and display it on an LED matrix."
    )
    
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Battery check interval in seconds (default: 5.0)"
    )
    
    parser.add_argument(
        "--brightness",
        type=int,
        default=50,
        help="LED matrix brightness (0-100, default: 50)"
    )
    
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="Index of the LED matrix device to use (default: 0)"
    )
    
    parser.add_argument(
        "--no-sound",
        action="store_true",
        help="Disable sound notifications"
    )
    
    parser.add_argument(
        "--plugged-sound",
        type=str,
        help="Path to custom sound file for plugged-in notification"
    )
    
    parser.add_argument(
        "--unplugged-sound",
        type=str,
        help="Path to custom sound file for unplugged notification"
    )
    
    return parser.parse_args()


def main():
    """
    Main function to run the battery monitor.
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Run any LED matrix package initialization (e.g., first-run welcome)
    init_led_matrix()
    
    # Get available LED matrix devices
    devices = get_devices()
    
    if not devices:
        print("Error: No LED matrix devices found.")
        print("Make sure your LED matrix is connected and recognized by the system.")
        sys.exit(1)
    
    # Select the specified device or default to the first one
    try:
        device = devices[args.device]
    except IndexError:
        print(f"Error: Device index {args.device} is out of range.")
        print(f"Available devices: {len(devices)}")
        sys.exit(1)
    
    # Create sound objects for notifications if not disabled
    plugged_alert = None
    unplugged_alert = None
    
    if not args.no_sound:
        if args.plugged_sound:
            plugged_path = Path(args.plugged_sound)
            if plugged_path.exists():
                plugged_alert = Sound(plugged_path)
            else:
                print(f"Warning: Plugged sound file not found: {plugged_path}")
                print("Using default sound instead.")
        
        if args.unplugged_sound:
            unplugged_path = Path(args.unplugged_sound)
            if unplugged_path.exists():
                unplugged_alert = Sound(unplugged_path)
            else:
                print(f"Warning: Unplugged sound file not found: {unplugged_path}")
                print("Using default sound instead.")
    
    # Initialize the LED matrix with the specified brightness
    led_matrix = LEDMatrix(device, args.brightness)
    
    print(f"Starting battery monitor with device: {device.device}")
    print(f"Battery check interval: {args.interval} seconds")
    print(f"LED matrix brightness: {args.brightness}%")
    print("Press Ctrl+C to exit")
    
    try:
        # Run the power monitor
        monitor = run_power_monitor(
            device,
            battery_check_interval=args.interval,
            plugged_alert=plugged_alert,
            unplugged_alert=unplugged_alert
        )
    except KeyboardInterrupt:
        print("\nBattery monitor stopped by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()