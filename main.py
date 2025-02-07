from enum import Enum, IntEnum
from typing import Literal

import pyautogui
import pygame


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
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


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


MAPPING_TO_KEYBOARD: dict[ZuikiMasconButton | DpadButton, str | tuple[str, str]] = {
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
    DpadButton.RIGHT: "k",
}


def key_down(button: ZuikiMasconButton | DpadButton) -> None:
    match MAPPING_TO_KEYBOARD[button]:
        case (*keys,):
            for key in keys:
                pyautogui.keyDown(key)
        case key:
            pyautogui.keyDown(key)


def key_up(button: ZuikiMasconButton | DpadButton) -> None:
    match MAPPING_TO_KEYBOARD[button]:
        case (*keys,):
            for key in reversed(keys):
                pyautogui.keyUp(key)
        case key:
            pyautogui.keyUp(key)


def handle_axis_motion(value: float) -> None:
    global notch

    if value > 0.9:
        next_notch = Notch.P5
    elif value > 0.7:
        next_notch = Notch.P4
    elif value > 0.55:
        next_notch = Notch.P3
    elif value > 0.35:
        next_notch = Notch.P2
    elif value > 0.15:
        next_notch = Notch.P1
    elif value > -0.1:
        next_notch = Notch.N
    elif value > -0.25:
        next_notch = Notch.B1
    elif value > -0.35:
        next_notch = Notch.B2
    elif value > -0.5:
        next_notch = Notch.B3
    elif value > -0.6:
        next_notch = Notch.B4
    elif value > -0.7:
        next_notch = Notch.B5
    elif value > -0.8:
        next_notch = Notch.B6
    elif value > -0.9:
        next_notch = Notch.B7
    elif ZuikiMasconButton.ZL in pressed_buttons:
        next_notch = Notch.EB
    else:
        next_notch = Notch.B8

    if next_notch == Notch.EB:
        pyautogui.press("1")
    elif next_notch == Notch.N:
        pyautogui.press("s")
    elif next_notch < notch:
        pyautogui.press("q", notch - next_notch)
    elif notch < next_notch:
        pyautogui.press("z", next_notch - notch)

    notch = next_notch


def handle_button_down(button: ZuikiMasconButton) -> None:
    global notch

    if button == ZuikiMasconButton.ZL:
        pressed_buttons.add(ZuikiMasconButton.ZL)
        if notch == Notch.B8:
            pyautogui.press("1")
            notch = Notch.EB
    else:
        key_down(button)


def handle_button_up(button: ZuikiMasconButton) -> None:
    global notch

    if button == ZuikiMasconButton.ZL:
        pressed_buttons.remove(ZuikiMasconButton.ZL)
        if notch == Notch.EB:
            pyautogui.press("z")
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


notch: Notch = Notch.N
pressed_buttons = set[Literal[ZuikiMasconButton.ZL] | DpadButton]()

pygame.init()
joystick = pygame.joystick.Joystick(0)

while True:
    for event in pygame.event.get():
        match event.type:
            case pygame.JOYAXISMOTION:
                handle_axis_motion(event.dict["value"])
            case pygame.JOYBUTTONDOWN:
                handle_button_down(event.dict["button"])
            case pygame.JOYBUTTONUP:
                handle_button_up(event.dict["button"])
            case pygame.JOYHATMOTION:
                handle_hat_motion(*event.dict["value"])
            case _:
                pass
