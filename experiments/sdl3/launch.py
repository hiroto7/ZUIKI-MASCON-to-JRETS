"""Run the existing UI with the pinned pygame-ce SDL3 experiment."""

import ctypes
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pygame

import main

if pygame.get_sdl_version()[0] != 3:
    raise RuntimeError("This launcher requires the SDL3 experiment environment")

sdl = ctypes.CDLL(str(Path(os.environ["ZUIKI_SDL3_ROOT"]) / "prefix/lib/libSDL3.dylib"))
sdl.SDL_GetJoysticks.argtypes = [ctypes.POINTER(ctypes.c_int)]
sdl.SDL_GetJoysticks.restype = ctypes.POINTER(ctypes.c_uint32)
sdl.SDL_free.argtypes = [ctypes.c_void_p]


def scan(self, unused=None):
    # SDL3 Joystick() takes instance IDs. The pinned pygame-ce still emits
    # device_index=-1 on connection, so rescan the IDs using the same SDL library.
    count = ctypes.c_int()
    ids = sdl.SDL_GetJoysticks(ctypes.byref(count))
    try:
        for i in range(count.value):
            if ids[i] not in self.joysticks:
                joystick = pygame.joystick.Joystick(ids[i])
                self.joysticks[joystick.get_instance_id()] = joystick
                print(
                    "CONNECTED",
                    joystick.get_name(),
                    "axes",
                    joystick.get_numaxes(),
                    "buttons",
                    joystick.get_numbuttons(),
                    flush=True,
                )
    finally:
        sdl.SDL_free(ids)


if __name__ == "__main__":
    main.MasconController.initialize_joysticks = scan
    main.MasconController.register_joystick = scan
    print(
        "WARNING: experimental SDL3 build; button mapping is not adjusted", flush=True
    )
    print("TEST BUILD", pygame.version.ver, "SDL", pygame.get_sdl_version(), flush=True)
    main.main()
