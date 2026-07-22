from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
import time

import pygame
import pyautogui
from pyautogui import press

INPUT_POLL_HZ = 60
PYGAME_POLL_INTERVAL_MS = 1000 // INPUT_POLL_HZ
EB_LAMP_TIMEOUT_SECONDS = 60.0


class TrainProfile(Enum):
    DEFAULT = auto()
    TOBU = auto()
    SEIBU = auto()


PROFILE_LABELS: dict[TrainProfile, str] = {
    TrainProfile.DEFAULT: "標準",
    TrainProfile.TOBU: "東武",
    TrainProfile.SEIBU: "西武",
}


class ZuikiMasconButton(IntEnum):
    A = 2
    B = 1
    X = 3
    Y = 0
    L = 4
    R = 5
    ZL = 6
    ZR = 7
    MINUS = 8
    PLUS = 9
    HOME = 12
    CAPTURE = 13


class DpadButton(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class Notch(IntEnum):
    P5 = 5
    P4 = 4
    P3 = 3
    P2 = 2
    P1 = 1
    N = 0
    B1 = -1
    B2 = -2
    B3 = -3
    B4 = -4
    B5 = -5
    B6 = -6
    B7 = -7
    B8 = -8
    EB = -9


@dataclass(frozen=True)
class ProfileLimit:
    max_power: Notch
    max_brake: Notch


@dataclass(frozen=True)
class ButtonMapping:
    keys: tuple[str, ...]
    resets_eb_timer: bool = False


PROFILE_LIMITS: dict[TrainProfile, ProfileLimit] = {
    TrainProfile.DEFAULT: ProfileLimit(max_power=Notch.P5, max_brake=Notch.B8),
    TrainProfile.TOBU: ProfileLimit(max_power=Notch.P3, max_brake=Notch.B7),
    TrainProfile.SEIBU: ProfileLimit(max_power=Notch.P4, max_brake=Notch.B7),
}


BUTTON_MAPPINGS: dict[ZuikiMasconButton | DpadButton, ButtonMapping] = {
    # 警笛（2段目）
    ZuikiMasconButton.A: ButtonMapping(("backspace",), resets_eb_timer=True),
    # 警笛（1段目）
    ZuikiMasconButton.B: ButtonMapping(("enter",), resets_eb_timer=True),
    # EBリセットボタン
    ZuikiMasconButton.X: ButtonMapping(("e",), resets_eb_timer=True),
    # ATS確認ボタン
    ZuikiMasconButton.Y: ButtonMapping(("space",)),
    # 警報持続ボタン
    ZuikiMasconButton.L: ButtonMapping(("x",)),
    # 抑速1
    ZuikiMasconButton.R: ButtonMapping(("d",)),
    # 定速/抑速2
    ZuikiMasconButton.ZR: ButtonMapping(("w",)),
    # 運転台表示切替
    ZuikiMasconButton.MINUS: ButtonMapping(("c",)),
    # ポーズ
    ZuikiMasconButton.PLUS: ButtonMapping(("esc",)),
    # [GeForce NOW] ゲーム内オーバーレイを開く / 閉じる
    ZuikiMasconButton.HOME: ButtonMapping(("command", "g")),
    # [GeForce NOW] スクリーンショットを保存する
    ZuikiMasconButton.CAPTURE: ButtonMapping(("command", "1")),
    # レバーサ 前位置方向
    DpadButton.UP: ButtonMapping(("up",)),
    # レバーサ 後位置方向
    DpadButton.DOWN: ButtonMapping(("down",)),
    # 連絡ブザースイッチ
    DpadButton.LEFT: ButtonMapping(("b",)),
    # 勾配起動ボタン
    DpadButton.RIGHT: ButtonMapping(("g",)),
}


def key_down(button: ZuikiMasconButton | DpadButton) -> None:
    for key in BUTTON_MAPPINGS[button].keys:
        pyautogui.keyDown(key)


def key_up(button: ZuikiMasconButton | DpadButton) -> None:
    for key in BUTTON_MAPPINGS[button].keys:
        pyautogui.keyUp(key)

        # 矢印キーを押すとfnキーが押されたような状態になる問題への回避策
        # https://github.com/asweigart/pyautogui/issues/796#issuecomment-1937049349
        if key in ("up", "down", "left", "right"):
            pyautogui.keyUp("fn")


def get_notch(value: float, is_zl_button_pressed: bool) -> Notch:  # noqa: C901
    if value > 0.9:
        return Notch.P5
    elif value > 0.7:
        return Notch.P4
    elif value > 0.55:
        return Notch.P3
    elif value > 0.35:
        return Notch.P2
    elif value > 0.15:
        return Notch.P1
    elif value > -0.1:
        return Notch.N
    elif value > -0.25:
        return Notch.B1
    elif value > -0.35:
        return Notch.B2
    elif value > -0.5:
        return Notch.B3
    elif value > -0.6:
        return Notch.B4
    elif value > -0.7:
        return Notch.B5
    elif value > -0.8:
        return Notch.B6
    elif value > -0.9:
        return Notch.B7
    elif is_zl_button_pressed:
        return Notch.EB
    else:
        return Notch.B8


def project_notch(raw_notch: Notch, profile_limit: ProfileLimit) -> Notch:
    if raw_notch >= Notch.P1:
        return min(raw_notch, profile_limit.max_power)
    elif Notch.EB < raw_notch <= Notch.B1:
        return max(raw_notch, profile_limit.max_brake)
    else:
        return raw_notch


def update_notch(current: Notch, next_notch: Notch, max_brake: Notch) -> None:
    if current == next_notch:
        return
    elif Notch.N <= current < next_notch:
        press("z", next_notch - current)
    elif current <= Notch.N and next_notch == Notch.EB:
        press("/")
    elif next_notch < current <= Notch.N:
        press(".", current - next_notch)
    elif current >= Notch.P1:
        if next_notch >= Notch.P1:
            press("a", current - next_notch)
        else:
            press("s")
            return update_notch(Notch.N, next_notch, max_brake)
    elif current <= Notch.B1:
        if next_notch <= Notch.B1:
            if current == Notch.EB:
                presses = next_notch - max_brake + 1
            else:
                presses = next_notch - current
            press(",", presses)
        else:
            press("m")
            return update_notch(Notch.N, next_notch, max_brake)


def effective_notch_order(profile_limit: ProfileLimit) -> tuple[Notch, ...]:
    return tuple(
        notch
        for notch in Notch
        if notch == Notch.EB
        or profile_limit.max_brake <= notch <= profile_limit.max_power
    )


@dataclass
class MasconController:
    profile: TrainProfile = TrainProfile.DEFAULT
    raw_notch: Notch = Notch.N
    pressed_buttons: set[ZuikiMasconButton | DpadButton] = field(default_factory=set)
    joysticks: dict[int, pygame.joystick.JoystickType] = field(default_factory=dict)
    last_driver_operation_at: float = field(default_factory=time.monotonic)
    eb_lamp_on: bool = False

    @property
    def profile_limit(self) -> ProfileLimit:
        return PROFILE_LIMITS[self.profile]

    @property
    def notch(self) -> Notch:
        return project_notch(self.raw_notch, self.profile_limit)

    def reset_eb_lamp_timer(self, now: float | None = None) -> None:
        self.last_driver_operation_at = time.monotonic() if now is None else now
        self.eb_lamp_on = False

    def update_eb_lamp(self, now: float | None = None) -> None:
        current_time = time.monotonic() if now is None else now
        self.eb_lamp_on = (
            current_time - self.last_driver_operation_at >= EB_LAMP_TIMEOUT_SECONDS
        )

    def handle_axis_motion(self, value: float) -> None:
        current_notch = self.notch
        next_raw_notch = get_notch(value, ZuikiMasconButton.ZL in self.pressed_buttons)
        next_notch = project_notch(next_raw_notch, self.profile_limit)

        update_notch(current_notch, next_notch, self.profile_limit.max_brake)

        self.raw_notch = next_raw_notch
        if next_notch != current_notch:
            self.reset_eb_lamp_timer()

    def handle_button_down(self, button: ZuikiMasconButton) -> None:
        self.pressed_buttons.add(button)
        if button == ZuikiMasconButton.ZL:
            if self.raw_notch == Notch.B8:
                update_notch(self.notch, Notch.EB, self.profile_limit.max_brake)
                self.raw_notch = Notch.EB
                self.reset_eb_lamp_timer()
        else:
            if BUTTON_MAPPINGS[button].resets_eb_timer:
                self.reset_eb_lamp_timer()
            key_down(button)

    def handle_button_up(self, button: ZuikiMasconButton) -> None:
        self.pressed_buttons.remove(button)
        if button == ZuikiMasconButton.ZL:
            if self.notch == Notch.EB:
                current_notch = self.notch
                self.raw_notch = Notch.B8
                next_notch = project_notch(self.raw_notch, self.profile_limit)
                update_notch(current_notch, next_notch, self.profile_limit.max_brake)
        else:
            key_up(button)

    def handle_hat_motion(self, x: int, y: int) -> None:
        for is_pressed, direction in (
            (y == 1, DpadButton.UP),
            (y == -1, DpadButton.DOWN),
            (x == -1, DpadButton.LEFT),
            (x == 1, DpadButton.RIGHT),
        ):
            if is_pressed and direction not in self.pressed_buttons:
                key_down(direction)
                self.pressed_buttons.add(direction)
            if not is_pressed and direction in self.pressed_buttons:
                key_up(direction)
                self.pressed_buttons.remove(direction)

    def change_profile(self, profile: TrainProfile) -> None:
        self.profile = profile

    def register_joystick(self, device_index: int) -> None:
        joystick = pygame.joystick.Joystick(device_index)
        self.joysticks[joystick.get_instance_id()] = joystick

    def initialize_joysticks(self) -> None:
        for device_index in range(pygame.joystick.get_count()):
            self.register_joystick(device_index)

    def unregister_joystick(self, instance_id: int) -> None:
        self.joysticks.pop(instance_id, None)

    def release_all_inputs(self) -> None:
        for button in list(self.pressed_buttons):
            if button != ZuikiMasconButton.ZL:
                key_up(button)
            self.pressed_buttons.discard(button)

    def print_state(self) -> None:
        print(
            self.notch.name,
            self.raw_notch.name,
            {button.name for button in self.pressed_buttons},
            self.eb_lamp_on,
        )
