"""Disable optional extensions in the pinned experimental pygame-ce source."""

import sys
from pathlib import Path

path = Path(sys.argv[1])
source = path.read_text()
for dependency, option in [
    ("sdl_image", "image"),
    ("sdl_ttf", "font"),
    ("sdl_mixer", "mixer"),
    ("freetype", "freetype"),
    ("portmidi", "midi"),
]:
    original = f"if {dependency}_dep.found()"
    replacement = f"{original} and not get_option('{option}').disabled()"
    if replacement not in source:
        if original not in source:
            raise RuntimeError(f"Unexpected upstream build configuration: {dependency}")
        source = source.replace(original, replacement)
path.write_text(source)
