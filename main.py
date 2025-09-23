import sys
from enum import Enum, IntEnum, auto

import pygame
from pynput.keyboard import Controller, Key


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


type KeyOrStr = str | Key

MAPPING_TO_KEYBOARD: dict[
    ZuikiMasconButton | DpadButton, KeyOrStr | tuple[KeyOrStr, ...]
] = {
    # 警笛（2段目）
    ZuikiMasconButton.A: Key.backspace,
    # 警笛（1段目）
    ZuikiMasconButton.B: Key.enter,
    # EBリセットボタン
    ZuikiMasconButton.X: "e",
    # ATS確認ボタン
    ZuikiMasconButton.Y: Key.space,
    # 警報持続ボタン
    ZuikiMasconButton.L: "x",
    # 抑速1
    ZuikiMasconButton.R: "d",
    # 定速/抑速2
    ZuikiMasconButton.ZR: "w",
    # 運転台表示切替
    ZuikiMasconButton.MINUS: "c",
    # ポーズ
    ZuikiMasconButton.PLUS: Key.esc,
    # [GeForce NOW] ゲーム内オーバーレイを開く / 閉じる
    ZuikiMasconButton.HOME: (Key.cmd, "g"),
    # [GeForce NOW] スクリーンショットを保存する
    ZuikiMasconButton.CAPTURE: (Key.cmd, "1"),
    # レバーサ 前位置方向
    DpadButton.UP: Key.up,
    # レバーサ 後位置方向
    DpadButton.DOWN: Key.down,
    # 連絡ブザースイッチ
    DpadButton.LEFT: "b",
    # 勾配起動ボタン
    DpadButton.RIGHT: "g",
}


def map_to_keys(button: ZuikiMasconButton | DpadButton) -> tuple[KeyOrStr, ...]:
    """
    Return the keyboard mapping for a given gamepad button as a tuple.
    
    Looks up `button` in MAPPING_TO_KEYBOARD and always returns a tuple of KeyOrStr:
    - If the mapping is already a tuple, it is returned unchanged.
    - If the mapping is a single key/string, it is returned as a one-element tuple.
    
    Parameters:
        button: A ZuikiMasconButton or DpadButton value to map.
    
    Returns:
        tuple[KeyOrStr, ...]: One or more keys/strings to be pressed for the given button.
    
    Notes:
        A KeyError will propagate if `button` is not present in MAPPING_TO_KEYBOARD.
    """
    match MAPPING_TO_KEYBOARD[button]:
        case tuple() as keys:
            return keys
        case key:
            return (key,)


def key_down(button: ZuikiMasconButton | DpadButton) -> None:
    """
    Presses the keyboard key(s) mapped to the given gamepad button.
    
    For the provided ZuikiMasconButton or DpadButton, looks up the mapped key or key sequence and issues a press for each mapped key using the global keyboard controller. This triggers key-down events only; keys are not released by this function.
    """
    for key in map_to_keys(button):
        keyboard.press(key)


def key_up(button: ZuikiMasconButton | DpadButton) -> None:
    """
    Release the keyboard keys mapped to the given gamepad button.
    
    Parameters:
        button (ZuikiMasconButton | DpadButton): The gamepad button whose mapped keyboard key(s) should be released.
    
    Notes:
        Uses the module's keyboard controller to release each key returned by map_to_keys(button).
    """
    for key in map_to_keys(button):
        keyboard.release(key)


def press_and_release(key: str, times: int = 1) -> None:
    """
    Press and release a keyboard key a number of times.
    
    Parameters:
        key (str | Key): The key to press; may be a character string or a pynput.keyboard.Key constant.
        times (int): Number of press/release cycles to perform (default 1).
    
    Returns:
        None
    """
    for _ in range(times):
        keyboard.press(key)
        keyboard.release(key)


def get_notch(value: float, is_zl_button_pressed: bool) -> Notch:
    """
    Map a joystick axis float value into a discrete Notch enum.
    
    The axis `value` is interpreted as a continuous input (expected range approximately -1.0..1.0)
    and is translated into one of the Notch positions (P5..P1, N, B1..B8, or EB) using fixed
    thresholds. If the axis falls below -0.9 and `is_zl_button_pressed` is True, the exclusive
    EB notch is returned; otherwise the deepest negative notch B8 is returned.
    
    Parameters:
        value (float): Axis position to classify (typically -1.0..1.0).
        is_zl_button_pressed (bool): When True allows returning Notch.EB for the extreme negative range.
    
    Returns:
        Notch: The discrete notch corresponding to `value`.
    """
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
    """
    Advance or rewind the current notch position by simulating the appropriate key sequences.
    
    Given the current and target Notch states, perform the minimal key press/release sequences (via press_and_release) required to move from current to next. Behavior by region:
    - From neutral toward positive (N <= current < next): press "z" repeated (next - current) times.
    - From any non-positive to EB (electronic boost): press "/" once.
    - From positive toward neutral (next < current <= N): press "." repeated (current - next) times.
    - From positive plateaus (current >= P1):
      - If staying within positive plateaus (next >= P1): press "a" repeated (current - next) times.
      - If moving out of positive into neutral/negative: press "s" once, then continue transition from Notch.N to next.
    - From negative plateaus (current <= B1):
      - If staying within negative plateaus (next <= B1): press "," repeated (next - current) times.
      - If moving out of negative into neutral/positive: press "m" once, then continue transition from Notch.N to next.
    
    Parameters:
        current (Notch): The current notch state.
        next (Notch): The target notch state.
    
    Returns:
        None
    
    Side effects:
        Triggers key press/release sequences through press_and_release; does not return a value.
    """
    if Notch.N <= current < next:
        press_and_release("z", next - current)
    elif current <= Notch.N and next == Notch.EB:
        press_and_release("/")
    elif next < current <= Notch.N:
        press_and_release(".", current - next)
    elif current >= Notch.P1:
        if next >= Notch.P1:
            press_and_release("a", current - next)
        else:
            press_and_release("s")
            return update_notch(Notch.N, next)
    elif current <= Notch.B1:
        if next <= Notch.B1:
            press_and_release(",", next - current)
        else:
            press_and_release("m")
            return update_notch(Notch.N, next)


def handle_axis_motion(value: float) -> None:
    global notch

    next_notch = get_notch(value, ZuikiMasconButton.ZL in pressed_buttons)
    update_notch(notch, next_notch)
    notch = next_notch


def handle_button_down(button: ZuikiMasconButton) -> None:
    """
    Handle a controller button press: record the button, trigger mapped key down actions, and handle the ZL notch transition.
    
    If the pressed button is ZL and the current notch is B8, sends a "/" press-and-release and sets the global notch to EB. For any other button, sends the configured key-down events for that button and adds it to the global pressed_buttons set.
    
    Parameters:
        button (ZuikiMasconButton): The gamepad button that was pressed.
    """
    global notch

    pressed_buttons.add(button)
    if button == ZuikiMasconButton.ZL:
        if notch == Notch.B8:
            press_and_release("/")
            notch = Notch.EB
    else:
        key_down(button)


def handle_button_up(button: ZuikiMasconButton) -> None:
    """
    Handle release of a controller button: update internal pressed set, adjust notch state when ZL is released, and release mapped keyboard keys.
    
    If `button` is ZL and the current global `notch` is EB, this triggers a comma press/release sequence and sets the global `notch` to B8. For any other button, the function releases the corresponding mapped keyboard key(s) via key_up.
    
    Parameters:
        button (ZuikiMasconButton): The controller button that was released.
    
    Side effects:
        - Removes `button` from the global `pressed_buttons` set.
        - May modify the global `notch`.
        - Simulates key releases (and in one case a press/release sequence).
    
    Raises:
        KeyError: If `button` is not present in `pressed_buttons`.
    """
    global notch

    pressed_buttons.remove(button)
    if button == ZuikiMasconButton.ZL:
        if notch == Notch.EB:
            press_and_release(",")
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
    pygame.display.set_allow_screensaver(True)

    keyboard = Controller()

    while True:
        for event in pygame.event.get():
            match event.type:
                case pygame.JOYDEVICEADDED:
                    joystick = pygame.joystick.Joystick(0)
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
