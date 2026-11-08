"""BMP slideshow for the Supercon 2026 CircuitPython badge.

Copy this file to CIRCUITPY/code.py and put BMP files in CIRCUITPY/images.
Uses only built-in modules. Images are centered without resizing.
Set the seconds per image in CIRCUITPY/refresh.txt (default: 30).
"""
import gc
import os
import time

import board
import displayio

IMAGE_FOLDER = "/images"
REFRESH_FILE = "/refresh.txt"
DEFAULT_SECONDS_PER_IMAGE = 30

display = board.DISPLAY
print("Slideshow display:", display.width, "x", display.height)

# A white background also clears the margins around smaller images.
background = displayio.Bitmap(1, 1, 1)
white = displayio.Palette(1)
white[0] = 0xFFFFFF
scene = displayio.Group()
backdrop = displayio.Group(scale=max(display.width, display.height))
backdrop.append(displayio.TileGrid(background, pixel_shader=white))
scene.append(backdrop)


def wait_for_display():
    while display.busy:
        time.sleep(0.1)


def read_refresh_seconds():
    # Re-read for each picture. Limit input size and reject invalid intervals.
    try:
        with open(REFRESH_FILE, "r") as settings:
            text = settings.read(1025)
        if len(text) > 1024:
            raise ValueError("refresh.txt is too long")
        values = []
        for line in text.splitlines():
            value = line.split("#", 1)[0].strip()
            if value:
                values.append(value)
        if len(values) != 1:
            raise ValueError("Use exactly one interval, with optional # comments")
        seconds = int(values[0])
        if not 1 <= seconds <= 86400:
            raise ValueError("Use a whole number from 1 to 86400")
        return seconds
    except (OSError, ValueError) as error:
        print("Using default refresh interval (30 seconds):", error)
        return DEFAULT_SECONDS_PER_IMAGE


def show_image(path):
    bitmap = None
    tile = None
    try:
        bitmap = displayio.OnDiskBitmap(path)
        if bitmap.width > display.width or bitmap.height > display.height:
            print("Skipping oversized image:", path, bitmap.width, bitmap.height)
            return False
        tile = displayio.TileGrid(
            bitmap,
            pixel_shader=bitmap.pixel_shader,
            x=(display.width - bitmap.width) // 2,
            y=(display.height - bitmap.height) // 2,
        )
        wait_for_display()
        scene.append(tile)
        display.root_group = scene
        # Keep the bitmap open until the asynchronous e-paper update is done.
        time.sleep(max(0, display.time_to_refresh) + 0.5)
        display.refresh()
        wait_for_display()
        print("Showing:", path)
        time.sleep(read_refresh_seconds())
        return True
    finally:
        wait_for_display()
        if tile is not None and len(scene) > 1:
            scene.pop()
        if bitmap is not None:
            bitmap.deinit()
        gc.collect()


while True:
    try:
        names = sorted(
            name for name in os.listdir(IMAGE_FOLDER)
            if not name.startswith(".") and name.lower().endswith(".bmp")
        )
    except OSError:
        names = []
        print("Create an images folder on CIRCUITPY and add BMP files.")

    shown = False
    for name in names:
        try:
            if show_image(IMAGE_FOLDER + "/" + name):
                shown = True
        except (OSError, ValueError, RuntimeError, MemoryError) as error:
            print("Could not show", name, ":", error)
    if not shown:
        print("Waiting for usable BMP images in", IMAGE_FOLDER)
        time.sleep(10)
