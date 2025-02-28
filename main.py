import sys
from enum import Enum, IntEnum, auto

import pygame
import pyautogui
from pyautogui import press


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


MAPPING_TO_KEYBOARD: dict[ZuikiMasconButton | DpadButton, str | tuple[str, ...]] = {
    # 警笛（2段目）
    ZuikiMasconButton.A: "backspace",
    # 警笛（1段目）
    ZuikiMasconButton.B: "enter",
    # EBリセットボタン
    ZuikiMasconButton.X: "e",
    # ATS確認ボタン
    ZuikiMasconButton.Y: "space",
    # 警報持続ボタン
    ZuikiMasconButton.L: "x",
    # 抑速1
    ZuikiMasconButton.R: "d",
    # 定速/抑速2
    ZuikiMasconButton.ZR: "w",
    # 運転台表示切替
    ZuikiMasconButton.MINUS: "c",
    # ポーズ
    ZuikiMasconButton.PLUS: "esc",
    # [GeForce NOW] ゲーム内オーバーレイを開く / 閉じる
    ZuikiMasconButton.HOME: ("command", "g"),
    # [GeForce NOW] スクリーンショットを保存する
    ZuikiMasconButton.CAPTURE: ("command", "1"),
    # レバーサ 前位置方向
    DpadButton.UP: "up",
    # レバーサ 後位置方向
    DpadButton.DOWN: "down",
    # 連絡ブザースイッチ
    DpadButton.LEFT: "b",
    # 勾配起動ボタン
    DpadButton.RIGHT: "g",
}


def map_to_keys(button: ZuikiMasconButton | DpadButton) -> tuple[str, ...]:
    match MAPPING_TO_KEYBOARD[button]:
        case tuple() as keys:
            return keys
        case key:
            return (key,)


def key_down(button: ZuikiMasconButton | DpadButton) -> None:
    for key in map_to_keys(button):
        pyautogui.keyDown(key)


def key_up(button: ZuikiMasconButton | DpadButton) -> None:
    for key in map_to_keys(button):
        pyautogui.keyUp(key)


def get_notch(value: float, is_zl_button_pressed: bool) -> Notch:
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


def update_notch(current: Notch, next: Notch) -> None:
    if Notch.N <= current < next:
        press("z", next - current)
    elif current <= Notch.N and next == Notch.EB:
        press("/")
    elif next < current <= Notch.N:
        press(".", current - next)
    elif current >= Notch.P1:
        if next >= Notch.P1:
            press("a", current - next)
        else:
            press("s")
            return update_notch(Notch.N, next)
    elif current <= Notch.B1:
        if next <= Notch.B1:
            press(",", next - current)
        else:
            press("m")
            return update_notch(Notch.N, next)


def handle_axis_motion(value: float) -> None:
    global notch

    next_notch = get_notch(value, ZuikiMasconButton.ZL in pressed_buttons)
    update_notch(notch, next_notch)
    notch = next_notch


def handle_button_down(button: ZuikiMasconButton) -> None:
    global notch

    pressed_buttons.add(button)
    if button == ZuikiMasconButton.ZL:
        if notch == Notch.B8:
            press("/")
            notch = Notch.EB
    else:
        key_down(button)


def handle_button_up(button: ZuikiMasconButton) -> None:
    global notch

    pressed_buttons.remove(button)
    if button == ZuikiMasconButton.ZL:
        if notch == Notch.EB:
            press(",")
            notch = Notch.B8
    else:
        key_up(button)


def handle_hat_motion(x: int, y: int) -> None:
    for is_pressed, direction in (
        (y == 1, DpadButton.UP),
        (y == -1, DpadButton.DOWN),
        (x == -1, DpadButton.LEFT),
        (x == 1, DpadButton.RIGHT),
    ):
        if is_pressed and direction not in pressed_buttons:
            key_down(direction)
            pressed_buttons.add(direction)
        if not is_pressed and direction in pressed_buttons:
            key_up(direction)
            pressed_buttons.remove(direction)


if __name__ == "__main__":
    notch: Notch = Notch.N
    pressed_buttons = set[ZuikiMasconButton | DpadButton]()

    pygame.init()
    joystick = pygame.joystick.Joystick(0)

    while True:
        for event in pygame.event.get():
            match event.type:
                case pygame.JOYAXISMOTION:
                    handle_axis_motion(event.dict["value"])
                case pygame.JOYBUTTONDOWN:
                    handle_button_down(ZuikiMasconButton(event.dict["button"]))
                case pygame.JOYBUTTONUP:
                    handle_button_up(ZuikiMasconButton(event.dict["button"]))
                case pygame.JOYHATMOTION:
                    handle_hat_motion(*event.dict["value"])
                case pygame.QUIT:
                    sys.exit()
                case _:
                    pass

            if "-v" in sys.argv[1:]:
                print(notch.name, {button.name for button in pressed_buttons})
