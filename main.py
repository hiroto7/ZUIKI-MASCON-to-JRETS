import argparse
import sys
from collections.abc import Callable
from typing import Protocol

import pygame

from mascon_controller import (
    INPUT_POLL_HZ,
    PYGAME_POLL_INTERVAL_MS,
    MasconController,
    TrainProfile,
    ZuikiMasconButton,
)


class TkRoot(Protocol):
    def after(self, ms: int, func: Callable[[], None]) -> object: ...

    def mainloop(self) -> None: ...


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=("default", "tobu", "seibu"),
        default="default",
        help="Train profile for notch limits. default preserves the previous behavior.",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without the tkinter status window.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def handle_pygame_events(
    controller: MasconController, args: argparse.Namespace
) -> None:
    for event in pygame.event.get():
        match event.type:
            case pygame.JOYDEVICEADDED:
                controller.register_joystick(event.dict["device_index"])
            case pygame.JOYDEVICEREMOVED:
                controller.unregister_joystick(event.dict["instance_id"])
            case pygame.JOYAXISMOTION:
                controller.handle_axis_motion(event.dict["value"])
            case pygame.JOYBUTTONDOWN:
                controller.handle_button_down(ZuikiMasconButton(event.dict["button"]))
            case pygame.JOYBUTTONUP:
                controller.handle_button_up(ZuikiMasconButton(event.dict["button"]))
            case pygame.JOYHATMOTION:
                controller.handle_hat_motion(*event.dict["value"])
            case pygame.QUIT:
                controller.release_all_inputs()
                sys.exit()
            case _:
                pass

        if args.verbose:
            controller.print_state()


def poll_pygame_events(
    root: TkRoot, controller: MasconController, args: argparse.Namespace
) -> None:
    handle_pygame_events(controller, args)
    root.after(
        PYGAME_POLL_INTERVAL_MS,
        lambda: poll_pygame_events(root, controller, args),
    )


def initialize_pygame(controller: MasconController) -> None:
    pygame.init()
    pygame.display.set_allow_screensaver(True)
    controller.initialize_joysticks()


def run_no_gui(controller: MasconController, args: argparse.Namespace) -> None:
    initialize_pygame(controller)

    clock = pygame.time.Clock()

    while True:
        handle_pygame_events(controller, args)
        clock.tick(INPUT_POLL_HZ)


def run_gui(controller: MasconController, args: argparse.Namespace) -> None:
    import tkinter as tk

    from status_window import StatusWindow

    root = tk.Tk()
    StatusWindow(root, controller)

    initialize_pygame(controller)

    poll_pygame_events(root, controller, args)
    root.mainloop()


if __name__ == "__main__":
    args = parse_args()
    controller = MasconController(profile=TrainProfile[args.profile.upper()])

    if args.no_gui:
        run_no_gui(controller, args)
    else:
        run_gui(controller, args)
