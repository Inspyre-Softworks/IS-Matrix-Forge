"""
Media display module for LED Matrix.

This module provides functions for displaying images and videos on the LED matrix.
It includes functions for rendering images, playing videos, and capturing from a camera.
"""

import serial
import time
import cv2
from PIL import Image

from ..constants import WIDTH, HEIGHT
from ..hardware import send_serial, send_command
from ..commands.map import CommandVals
from . import send_col, commit_cols
from is_matrix_forge.led_matrix.helpers.status_handler import get_status, set_status


def image(dev, image_file):
    """Display a black/white image
    Send everything in a single command"""
    # Initialize a byte array to hold the binary representation of the image
    # 39 bytes = 312 bits, which is enough for 9x34 = 306 pixels
    vals = [0x00 for _ in range(39)]

    # Open and convert the image to RGB format
    im = Image.open(image_file).convert("RGB")
    width, height = im.size

    # Verify image dimensions match the LED matrix size
    assert width == 9
    assert height == 34

    # Get all pixel values as a flat list
    pixel_values = list(im.getdata())

    # Process each pixel
    for i, pixel in enumerate(pixel_values):
        # Calculate average brightness of RGB components
        brightness = sum(pixel) / 3

        # If brightness is above half of max (127.5), consider it "on"
        # This creates a binary black/white effect
        if brightness > 0xFF / 2:
            # Calculate which byte in vals array this pixel belongs to (i/8)
            # Then set the appropriate bit within that byte (i%8)
            # This packs 8 pixels into each byte of the vals array
            vals[int(i / 8)] |= 1 << i % 8

    # Send the packed binary data to the device
    send_command(dev, CommandVals.Draw, vals)


def pixel_to_brightness(pixel):
    """Calculate pixel brightness from an RGB triple"""
    assert len(pixel) == 3
    brightness = sum(pixel) / len(pixel)

    # Poor man's scaling to make the greyscale pop better.
    # Should find a good function.
    if brightness > 200:
        brightness = brightness
    elif brightness > 150:
        brightness = brightness * 0.8
    elif brightness > 100:
        brightness = brightness * 0.5
    elif brightness > 50:
        brightness = brightness
    else:
        brightness = brightness * 2

    return int(brightness)


def image_greyscale(dev, image_file):
    """Display an image in greyscale
    Sends each 1x34 column and then commits => 10 commands
    """
    with serial.Serial(dev.device, 115200) as s:
        from PIL import Image

        im = Image.open(image_file).convert("RGB")
        width, height = im.size
        assert width == 9
        assert height == 34
        pixel_values = list(im.getdata())
        for x in range(0, WIDTH):
            vals = [0 for _ in range(HEIGHT)]

            for y in range(HEIGHT):
                vals[y] = pixel_to_brightness(pixel_values[x + y * WIDTH])

            send_col(dev, s, x, vals)
        commit_cols(dev, s)


def camera(dev):
    """Play a live view from the webcam, for fun"""
    set_status('camera')
    with serial.Serial(dev.device, 115200) as s:
        import cv2

        capture = cv2.VideoCapture(1)
        ret, frame = capture.read()

        scale_y = HEIGHT / frame.shape[0]

        # Scale the video to 34 pixels height
        dim = (HEIGHT, int(round(frame.shape[1] * scale_y)))
        # Find the starting position to crop the width to be centered
        # For very narrow videos, make sure to stay in bounds
        start_x = max(0, int(round(dim[1] / 2 - WIDTH / 2)))
        end_x = min(dim[1], start_x + WIDTH)

        # Pre-process the video into resized, cropped, grayscale frames
        while get_status() == 'camera':
            ret, frame = capture.read()
            if not ret:
                print("Failed to capture video frames")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            resized = cv2.resize(gray, (dim[1], dim[0]))
            cropped = resized[0:HEIGHT, start_x:end_x]

            for x in range(0, cropped.shape[1]):
                vals = [0 for _ in range(HEIGHT)]

                for y in range(0, HEIGHT):
                    vals[y] = cropped[y, x]

                send_col(dev, s, x, vals)
            commit_cols(dev, s)


def video(dev, video_file):
    """Resize and play back a video"""
    set_status('video')
    with serial.Serial(dev.device, 115200) as s:
        import cv2

        capture = cv2.VideoCapture(video_file)
        ret, frame = capture.read()

        scale_y = HEIGHT / frame.shape[0]

        # Scale the video to 34 pixels height
        dim = (HEIGHT, int(round(frame.shape[1] * scale_y)))
        # Find the starting position to crop the width to be centered
        # For very narrow videos, make sure to stay in bounds
        start_x = max(0, int(round(dim[1] / 2 - WIDTH / 2)))
        end_x = min(dim[1], start_x + WIDTH)

        processed = []

        # Pre-process the video into resized, cropped, grayscale frames
        while get_status() == 'video':
            ret, frame = capture.read()
            if not ret:
                print("Failed to read video frames")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            resized = cv2.resize(gray, (dim[1], dim[0]))
            cropped = resized[0:HEIGHT, start_x:end_x]

            processed.append(cropped)

        # Determine frame delay based on the video's FPS.  Fall back to 30 FPS
        # if the FPS value cannot be obtained.
        fps = capture.get(cv2.CAP_PROP_FPS)
        try:
            fps = float(fps)
            if fps <= 0 or fps != fps:
                raise ValueError
        except Exception:
            fps = 30.0
        frame_delay = 1.0 / fps

        # Write it out to the module one frame at a time while respecting the
        # original frame rate.
        for frame in processed:
            start = time.time()
            for x in range(0, cropped.shape[1]):
                vals = [0 for _ in range(HEIGHT)]

                for y in range(0, HEIGHT):
                    vals[y] = frame[y, x]

                send_col(dev, s, x, vals)
            commit_cols(dev, s)

            elapsed = time.time() - start
            if frame_delay > elapsed:
                time.sleep(frame_delay - elapsed)
