import argparse
import json
import queue
import socket
import sys
import threading
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pygame
import pyautogui
from pyautogui import press


class TrainProfile(Enum):
    DEFAULT = auto()
    TOBU = auto()
    SEIBU = auto()


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


PROFILE_LIMITS: dict[TrainProfile, ProfileLimit] = {
    TrainProfile.DEFAULT: ProfileLimit(max_power=Notch.P5, max_brake=Notch.B8),
    TrainProfile.TOBU: ProfileLimit(max_power=Notch.P3, max_brake=Notch.B7),
    TrainProfile.SEIBU: ProfileLimit(max_power=Notch.P4, max_brake=Notch.B7),
}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=("default", "tobu", "seibu"),
        default="default",
        help="Train profile for notch limits. default preserves the previous behavior.",
    )
    parser.add_argument(
        "--fake-notch-web",
        action="store_true",
        help="Serve a phone-friendly web controller for fake mascon notch input.",
    )
    parser.add_argument(
        "--fake-notch-web-host",
        default="0.0.0.0",
        help="Host for --fake-notch-web. Use 0.0.0.0 to accept phone connections.",
    )
    parser.add_argument(
        "--fake-notch-web-port",
        type=int,
        default=8765,
        help="Port for --fake-notch-web.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


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

        # 矢印キーを押すとfnキーが押されたような状態になる問題への回避策
        # https://github.com/asweigart/pyautogui/issues/796#issuecomment-1937049349
        if key in ("up", "down", "left", "right"):
            pyautogui.keyUp("fn")


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


def fake_notch_options(profile_limit: ProfileLimit) -> tuple[Notch, ...]:
    return tuple(
        reversed(
            tuple(
                notch
                for notch in Notch
                if notch == Notch.EB
                or profile_limit.max_brake <= notch <= profile_limit.max_power
            )
        )
    )


def build_fake_notch_web_html(
    profile_name: str,
    current_notch: Notch,
    profile_limit: ProfileLimit,
) -> bytes:
    notch_names = tuple(notch.name for notch in fake_notch_options(profile_limit))
    notch_labels = "\n".join(
        f'      <button class="tick" type="button" data-notch="{notch_name}">'
        f"{notch_name}</button>"
        for notch_name in notch_names
    )
    template = (Path(__file__).with_name("web") / "fake_notch.html").read_text()
    html = (
        template.replace("__PROFILE_NAME__", profile_name)
        .replace("__NOTCH_LABELS__", notch_labels)
        .replace("__NOTCH_NAMES_JSON__", json.dumps(notch_names))
        .replace("__CURRENT_NOTCH__", current_notch.name)
    )
    return html.encode()


def get_lan_ip() -> str | None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return None


def make_fake_notch_web_handler(
    input_queue: queue.Queue[Notch],
    profile_name: str,
    current_notch: Notch,
    profile_limit: ProfileLimit,
) -> type[BaseHTTPRequestHandler]:
    class FakeNotchWebHandler(BaseHTTPRequestHandler):
        def send_json(self, status: HTTPStatus, body: dict[str, object]) -> None:
            encoded = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def read_json(self) -> dict[str, object]:
            length = int(self.headers.get("content-length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:
            if self.path not in ("/", "/index.html"):
                self.send_json(HTTPStatus.NOT_FOUND, {"ok": False})
                return

            body = build_fake_notch_web_html(
                profile_name,
                current_notch,
                profile_limit,
            )
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            try:
                payload = self.read_json()
                if self.path != "/notch":
                    self.send_json(HTTPStatus.NOT_FOUND, {"ok": False})
                    return

                next_notch = Notch[str(payload["notch"])]
                if next_notch not in fake_notch_options(profile_limit):
                    raise ValueError("unsupported notch for profile")
                input_queue.put(next_notch)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
                return

            self.send_json(HTTPStatus.OK, {"ok": True})

        def log_message(self, format: str, *args: object) -> None:
            return

    return FakeNotchWebHandler


def start_fake_notch_web_server(
    host: str,
    port: int,
    input_queue: queue.Queue[Notch],
    profile_name: str,
    current_notch: Notch,
    profile_limit: ProfileLimit,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        (host, port),
        make_fake_notch_web_handler(
            input_queue,
            profile_name,
            current_notch,
            profile_limit,
        ),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    actual_port = server.server_address[1]
    print(f"Fake notch web controller: http://127.0.0.1:{actual_port}/")
    if host in ("0.0.0.0", "") and (lan_ip := get_lan_ip()):
        print(f"Phone URL: http://{lan_ip}:{actual_port}/")
    return server


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


def handle_axis_motion(value: float) -> None:
    global raw_notch
    global notch

    next_raw_notch = get_notch(value, ZuikiMasconButton.ZL in pressed_buttons)
    next_notch = project_notch(next_raw_notch, profile_limit)

    update_notch(notch, next_notch, profile_limit.max_brake)

    raw_notch = next_raw_notch
    notch = next_notch


def handle_fake_notch_input(next_notch: Notch) -> None:
    global raw_notch
    global notch

    update_notch(notch, next_notch, profile_limit.max_brake)

    raw_notch = next_notch
    notch = next_notch


def handle_button_down(button: ZuikiMasconButton) -> None:
    global raw_notch
    global notch

    pressed_buttons.add(button)
    if button == ZuikiMasconButton.ZL:
        if raw_notch == Notch.B8:
            update_notch(notch, Notch.EB, profile_limit.max_brake)
            raw_notch = Notch.EB
            notch = Notch.EB
    else:
        key_down(button)


def handle_button_up(button: ZuikiMasconButton) -> None:
    global raw_notch
    global notch

    pressed_buttons.remove(button)
    if button == ZuikiMasconButton.ZL:
        if notch == Notch.EB:
            raw_notch = Notch.B8
            next_notch = project_notch(raw_notch, profile_limit)
            update_notch(notch, next_notch, profile_limit.max_brake)
            notch = next_notch
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


def print_state() -> None:
    print(notch.name, raw_notch.name, {button.name for button in pressed_buttons})


if __name__ == "__main__":
    args = parse_args()
    profile = TrainProfile[args.profile.upper()]
    profile_limit = PROFILE_LIMITS[profile]

    raw_notch: Notch = Notch.N
    notch: Notch = Notch.N
    pressed_buttons = set[ZuikiMasconButton | DpadButton]()
    fake_notch_web_queue: queue.Queue[Notch] | None = None
    fake_notch_web_server: ThreadingHTTPServer | None = None

    pygame.init()
    pygame.display.set_allow_screensaver(True)
    if args.fake_notch_web:
        fake_notch_web_queue = queue.Queue()
        fake_notch_web_server = start_fake_notch_web_server(
            args.fake_notch_web_host,
            args.fake_notch_web_port,
            fake_notch_web_queue,
            args.profile,
            notch,
            profile_limit,
        )

    clock = pygame.time.Clock()

    while True:
        if fake_notch_web_queue is not None:
            while not fake_notch_web_queue.empty():
                handle_fake_notch_input(fake_notch_web_queue.get())
                if args.verbose:
                    print_state()

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
                    if fake_notch_web_server is not None:
                        fake_notch_web_server.shutdown()
                    sys.exit()
                case _:
                    pass

            if args.verbose:
                print_state()

        clock.tick(60)
