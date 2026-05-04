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
        "--fake-axis-web",
        action="store_true",
        help="Serve a phone-friendly web controller for fake mascon axis input.",
    )
    parser.add_argument(
        "--fake-axis-web-host",
        default="0.0.0.0",
        help="Host for --fake-axis-web. Use 0.0.0.0 to accept phone connections.",
    )
    parser.add_argument(
        "--fake-axis-web-port",
        type=int,
        default=8765,
        help="Port for --fake-axis-web.",
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


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def build_fake_axis_web_html(profile_name: str) -> bytes:
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
  <title>ZUIKI fake axis</title>
  <style>
    html, body {{
      margin: 0;
      height: 100%;
      background: #15191d;
      color: #eef2f6;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      overscroll-behavior: none;
      touch-action: none;
    }}
    body {{
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 12px;
      padding: 16px;
      box-sizing: border-box;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      font-size: 15px;
    }}
    #pad {{
      position: relative;
      border: 1px solid #55616f;
      background: #222a31;
      border-radius: 10px;
      min-height: 420px;
      overflow: hidden;
    }}
    #rail {{
      position: absolute;
      top: 24px;
      bottom: 24px;
      left: 50%;
      border-left: 2px solid #a8b3bf;
    }}
    #handle {{
      position: absolute;
      left: 50%;
      width: 42px;
      height: 42px;
      margin-left: -21px;
      margin-top: -21px;
      border-radius: 50%;
      background: #f4f7fb;
      box-shadow: 0 0 0 5px rgba(244, 247, 251, 0.18);
    }}
    #labels {{
      position: absolute;
      inset: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      pointer-events: none;
      color: #a8b3bf;
      font-weight: 700;
    }}
    footer {{
      display: grid;
      grid-template-columns: 1fr 110px;
      gap: 12px;
      align-items: stretch;
    }}
    #value {{
      border: 1px solid #55616f;
      border-radius: 8px;
      padding: 14px;
      color: #d5dce5;
      font-variant-numeric: tabular-nums;
    }}
    #zl {{
      border: 0;
      border-radius: 8px;
      background: #c53939;
      color: white;
      font-size: 22px;
      font-weight: 800;
      touch-action: none;
    }}
    #zl.active {{
      background: #ff5555;
    }}
  </style>
</head>
<body>
  <header>
    <strong>ZUIKI fake axis</strong>
    <span>profile: {profile_name}</span>
  </header>
  <main id="pad">
    <div id="rail"></div>
    <div id="handle"></div>
    <div id="labels"><span>P5</span><span>N</span><span>B8</span></div>
  </main>
  <footer>
    <div id="value">value=0.000</div>
    <button id="zl" type="button">ZL</button>
  </footer>
  <script>
    const pad = document.getElementById("pad");
    const handle = document.getElementById("handle");
    const valueLabel = document.getElementById("value");
    const zl = document.getElementById("zl");
    let activePointer = null;
    let lastAxisSent = 0;

    function clamp(value, lower, upper) {{
      return Math.max(lower, Math.min(upper, value));
    }}

    function valueFromPointer(event) {{
      const rect = pad.getBoundingClientRect();
      const y = clamp(event.clientY - rect.top, 0, rect.height);
      return 1 - (y / rect.height) * 2;
    }}

    function render(value) {{
      const rect = pad.getBoundingClientRect();
      const y = (1 - value) * rect.height / 2;
      handle.style.top = `${{y}}px`;
      valueLabel.textContent = `value=${{value.toFixed(3)}}`;
    }}

    function postJson(path, payload) {{
      return fetch(path, {{
        method: "POST",
        headers: {{"content-type": "application/json"}},
        body: JSON.stringify(payload),
        keepalive: true,
      }}).catch(() => undefined);
    }}

    function sendAxis(value, force = false) {{
      const now = performance.now();
      if (!force && now - lastAxisSent < 33) {{
        render(value);
        return;
      }}
      lastAxisSent = now;
      render(value);
      postJson("/axis", {{value}});
    }}

    pad.addEventListener("pointerdown", (event) => {{
      activePointer = event.pointerId;
      pad.setPointerCapture(event.pointerId);
      sendAxis(valueFromPointer(event), true);
    }});

    pad.addEventListener("pointermove", (event) => {{
      if (activePointer !== event.pointerId) return;
      sendAxis(valueFromPointer(event));
    }});

    pad.addEventListener("pointerup", (event) => {{
      if (activePointer !== event.pointerId) return;
      sendAxis(valueFromPointer(event), true);
      activePointer = null;
    }});

    pad.addEventListener("pointercancel", () => {{
      activePointer = null;
    }});

    zl.addEventListener("pointerdown", (event) => {{
      event.preventDefault();
      zl.classList.add("active");
      postJson("/button", {{button: "ZL", pressed: true}});
    }});

    function releaseZl() {{
      zl.classList.remove("active");
      postJson("/button", {{button: "ZL", pressed: false}});
    }}

    zl.addEventListener("pointerup", releaseZl);
    zl.addEventListener("pointercancel", releaseZl);
    window.addEventListener("blur", releaseZl);

    render(0);
    sendAxis(0, true);
  </script>
</body>
</html>
""".encode()


def get_lan_ip() -> str | None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return None


def make_fake_axis_web_handler(
    input_queue: queue.Queue[tuple[str, float | bool]],
    profile_name: str,
) -> type[BaseHTTPRequestHandler]:
    class FakeAxisWebHandler(BaseHTTPRequestHandler):
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

            body = build_fake_axis_web_html(profile_name)
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            try:
                payload = self.read_json()
                if self.path == "/axis":
                    value = clamp(float(payload["value"]), -1.0, 1.0)
                    input_queue.put(("axis", value))
                elif self.path == "/button":
                    if payload.get("button") != "ZL":
                        raise ValueError("unsupported button")
                    input_queue.put(("zl", bool(payload["pressed"])))
                else:
                    self.send_json(HTTPStatus.NOT_FOUND, {"ok": False})
                    return
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
                return

            self.send_json(HTTPStatus.OK, {"ok": True})

        def log_message(self, format: str, *args: object) -> None:
            return

    return FakeAxisWebHandler


def start_fake_axis_web_server(
    host: str,
    port: int,
    input_queue: queue.Queue[tuple[str, float | bool]],
    profile_name: str,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(
        (host, port),
        make_fake_axis_web_handler(input_queue, profile_name),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    actual_port = server.server_address[1]
    print(f"Fake axis web controller: http://127.0.0.1:{actual_port}/")
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
    fake_axis_web_queue: queue.Queue[tuple[str, float | bool]] | None = None
    fake_axis_web_server: ThreadingHTTPServer | None = None

    pygame.init()
    pygame.display.set_allow_screensaver(True)
    if args.fake_axis_web:
        fake_axis_web_queue = queue.Queue()
        fake_axis_web_server = start_fake_axis_web_server(
            args.fake_axis_web_host,
            args.fake_axis_web_port,
            fake_axis_web_queue,
            args.profile,
        )

    clock = pygame.time.Clock()

    while True:
        should_print_state = False

        if fake_axis_web_queue is not None:
            while not fake_axis_web_queue.empty():
                kind, value = fake_axis_web_queue.get()
                if kind == "axis":
                    handle_axis_motion(float(value))
                    should_print_state = True
                elif kind == "zl" and value:
                    if ZuikiMasconButton.ZL not in pressed_buttons:
                        handle_button_down(ZuikiMasconButton.ZL)
                        should_print_state = True
                elif kind == "zl":
                    if ZuikiMasconButton.ZL in pressed_buttons:
                        handle_button_up(ZuikiMasconButton.ZL)
                        should_print_state = True

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
                    if fake_axis_web_server is not None:
                        fake_axis_web_server.shutdown()
                    sys.exit()
                case _:
                    pass

            if args.verbose:
                print_state()

        if args.verbose and should_print_state:
            print_state()

        clock.tick(60)
