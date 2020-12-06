"""
Generate a palette using various backends.
"""
import logging
import os
import random
import re
import sys
from math import sqrt

from . import theme
from . import util
from .settings import CACHE_DIR, MODULE_DIR, __cache_version__

x_colors_b = [
        (0, 0, 0),       # Black
        (205, 0, 0),     # Red
        (0, 205, 0),     # Green
        (205, 205, 0),   # Yellow
        (0, 0, 238),     # Blue
        (205, 0, 205),   # Magenta
        (0, 205, 205),   # Cyan
        (229, 229, 229), # White
        (255, 0, 0),     # Bright Red
        (0, 255, 0),     # Bright Green       
        (255, 255, 0),   # Bright Yellow  
        (92, 92, 255),   # Bright Blue
        (255, 0, 255),   # Bright Magenta
        (0, 255, 255),   # Bright Cyan        
        (127, 127, 127), # Bright Black (Gray)
        (255, 255, 255), # Bright White       
        ]

x_colors = [(r / 255.0, g / 255.0, b / 255.0) for r, g, b in x_colors_b]

def list_backends():
    """List color backends."""
    return [b.name.replace(".py", "") for b in
            os.scandir(os.path.join(MODULE_DIR, "backends"))
            if "__" not in b.name]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

def color_diff(rgb1, hex_color2):
    (r1, g1, b1) = rgb1
    (r2, g2, b2) = hex_to_rgb(hex_color2)
    return sqrt((r2 - r1) ** 2 + (g2 - g1) ** 2 + (b2 - b1) ** 2)

def match_colors(colors):
    out = [None] * len(colors)
    cs = colors.copy()
    for i, x_color in enumerate(x_colors):
        l = lambda x: color_diff(x_color, x)
        desired = min(cs, key=l) 
        out[i] = desired
        cs.remove(desired)
    return out

def colors_to_dict(colors, img):
    """Convert list of colors to pywal format."""
    cs = match_colors(colors)
    ok = {'color{}'.format(i): v for i, v in enumerate(cs)}
    return {
        "wallpaper": img,
        "alpha": util.Color.alpha_num,

        "special": {
            "background": cs[0],
            "foreground": cs[15],
            "cursor": cs[15]
        },

        "colors": ok
    }


def generic_adjust(colors, light):
    """Generic color adjustment for themers."""
    if light:
        for color in colors:
            color = util.saturate_color(color, 0.60)
            color = util.darken_color(color, 0.5)

        colors[0] = util.lighten_color(colors[0], 0.95)
        colors[7] = util.darken_color(colors[0], 0.75)
        colors[8] = util.darken_color(colors[0], 0.25)
        colors[15] = colors[7]

    else:
        colors[0] = util.darken_color(colors[0], 0.80)
        colors[7] = util.lighten_color(colors[0], 0.75)
        colors[8] = util.lighten_color(colors[0], 0.25)
        colors[15] = colors[7]

    return colors


def saturate_colors(colors, amount):
    """Saturate all colors."""
    if amount and float(amount) <= 1.0:
        for i, _ in enumerate(colors):
            if i not in [0, 7, 8, 15]:
                colors[i] = util.saturate_color(colors[i], float(amount))

    return colors


def cache_fname(img, backend, light, cache_dir, sat=""):
    """Create the cache file name."""
    color_type = "light" if light else "dark"
    file_name = re.sub("[/|\\|.]", "_", img)
    file_size = os.path.getsize(img)

    file_parts = [file_name, color_type, backend,
                  sat, file_size, __cache_version__]
    return [cache_dir, "schemes", "%s_%s_%s_%s_%s_%s.json" % (*file_parts,)]


def get_backend(backend):
    """Figure out which backend to use."""
    if backend == "random":
        backends = list_backends()
        random.shuffle(backends)
        return backends[0]

    return backend


def palette():
    """Generate a palette from the colors."""
    for i in range(0, 16):
        if i % 8 == 0:
            print()

        if i > 7:
            i = "8;5;%s" % i

        print("\033[4%sm%s\033[0m" % (i, " " * (80 // 20)), end="")

    print("\n")


def get(img, light=False, backend="wal", cache_dir=CACHE_DIR, sat=""):
    """Generate a palette."""
    # home_dylan_img_jpg_backend_1.2.2.json
    cache_name = cache_fname(img, backend, light, cache_dir, sat)
    cache_file = os.path.join(*cache_name)

    if os.path.isfile(cache_file):
        colors = theme.file(cache_file)
        colors["alpha"] = util.Color.alpha_num
        logging.info("Found cached colorscheme.")

    else:
        logging.info("Generating a colorscheme.")
        backend = get_backend(backend)

        # Dynamically import the backend we want to use.
        # This keeps the dependencies "optional".
        try:
            __import__("pywal.backends.%s" % backend)
        except ImportError:
            __import__("pywal.backends.wal")
            backend = "wal"

        logging.info("Using %s backend.", backend)
        backend = sys.modules["pywal.backends.%s" % backend]
        colors = getattr(backend, "get")(img, light)
        colors = colors_to_dict(saturate_colors(colors, sat), img)

        util.save_file_json(colors, cache_file)
        logging.info("Generation complete.")

    return colors


def file(input_file):
    """Deprecated: symbolic link to --> theme.file"""
    return theme.file(input_file)
