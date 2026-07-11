import threading
from _thread import RLock
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import pygame
import webview

from accessibility_permission import (
    is_accessibility_permission_granted,
    is_macos,
    open_accessibility_settings,
)
from mascon_controller import (
    PROFILE_LABELS,
    PYGAME_POLL_INTERVAL_MS,
    MasconController,
    TrainProfile,
    effective_notch_order,
)
from version_info import BUILD_LABEL

WINDOW_TITLE = "ZUIKI MASCON to JRETS"
WINDOW_WIDTH = 760
WINDOW_HEIGHT = 520
WEB_ROOT = Path(__file__).resolve().parent / "web"


class ProfileStatus(TypedDict):
    id: str
    label: str
    selected: bool


class StatusSnapshot(TypedDict):
    notch: str
    raw_notch: str
    notch_order: list[str]
    profile: str
    profiles: list[ProfileStatus]
    max_power: str
    max_brake: str
    controller_count: int
    pressed_buttons: list[str]
    show_accessibility: bool
    accessibility_granted: bool
    build_label: str


def build_status_snapshot(
    controller: MasconController,
    *,
    show_accessibility: bool | None = None,
    accessibility_granted: bool | None = None,
) -> StatusSnapshot:
    if show_accessibility is None:
        show_accessibility = is_macos()
    if accessibility_granted is None:
        accessibility_granted = (
            is_accessibility_permission_granted() if show_accessibility else True
        )
    return {
        "notch": controller.notch.name,
        "raw_notch": controller.raw_notch.name,
        "notch_order": [
            notch.name for notch in effective_notch_order(controller.profile_limit)
        ],
        "profile": controller.profile.name.lower(),
        "profiles": [
            {
                "id": profile.name.lower(),
                "label": label,
                "selected": profile == controller.profile,
            }
            for profile, label in PROFILE_LABELS.items()
        ],
        "max_power": controller.profile_limit.max_power.name,
        "max_brake": controller.profile_limit.max_brake.name,
        "controller_count": len(controller.joysticks),
        "pressed_buttons": sorted(button.name for button in controller.pressed_buttons),
        "show_accessibility": show_accessibility,
        "accessibility_granted": accessibility_granted,
        "build_label": BUILD_LABEL,
    }


class StatusApi:
    def __init__(
        self,
        controller: MasconController,
        controller_lock: RLock | None = None,
    ) -> None:
        self._controller = controller
        self._controller_lock = controller_lock or RLock()

    def get_status(self) -> StatusSnapshot:
        show_accessibility = is_macos()
        accessibility_granted = (
            is_accessibility_permission_granted() if show_accessibility else True
        )
        with self._controller_lock:
            return build_status_snapshot(
                self._controller,
                show_accessibility=show_accessibility,
                accessibility_granted=accessibility_granted,
            )

    def change_profile(self, profile_id: str) -> StatusSnapshot:
        try:
            profile = TrainProfile[profile_id.upper()]
        except KeyError as error:
            raise ValueError(f"Unknown train profile: {profile_id}") from error

        with self._controller_lock:
            self._controller.change_profile(profile)
        return self.get_status()

    def open_accessibility_settings(self) -> None:
        open_accessibility_settings()


class StatusWindow:
    def __init__(
        self,
        controller: MasconController,
        poll_events: Callable[[], None],
    ) -> None:
        self.controller = controller
        self.poll_events = poll_events
        self.stop_event = threading.Event()
        self.controller_lock = RLock()
        self.api = StatusApi(controller, self.controller_lock)
        window = webview.create_window(  # pyright: ignore[reportUnknownMemberType]
            WINDOW_TITLE,
            str(WEB_ROOT / "index.html"),
            js_api=self.api,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(640, 440),
            resizable=True,
            background_color="#09111f",
            text_select=False,
        )
        if window is None:
            raise RuntimeError("Failed to create the status window")
        self.window = window
        self.window.events.closed += self.close

    def run(self) -> None:
        webview.start(self.poll_loop)

    def poll_loop(self) -> None:
        interval_seconds = PYGAME_POLL_INTERVAL_MS / 1000
        while not self.stop_event.wait(interval_seconds):
            with self.controller_lock:
                self.poll_events()

    def close(self) -> None:
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        with self.controller_lock:
            self.controller.release_all_inputs()
        pygame.quit()
