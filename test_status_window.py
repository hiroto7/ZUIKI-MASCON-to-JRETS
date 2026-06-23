import sys
from unittest.mock import Mock

mock = Mock()
sys.modules["pyautogui"] = mock

import status_window  # noqa: E402
from status_window import (  # noqa: E402
    ACCESSIBILITY_PERMISSION_POLL_INTERVAL_MS,
    accessibility_permission_status,
)


def test_accessibility_permission_status_when_granted() -> None:
    text, color, help_text = accessibility_permission_status(True)

    assert text == "アクセシビリティ権限: 許可済み"
    assert color == "#57606a"
    assert help_text == ""


def test_accessibility_permission_status_when_denied() -> None:
    text, color, help_text = accessibility_permission_status(False)

    assert text == "アクセシビリティ権限: 未許可"
    assert color == "#b42318"
    assert help_text == "システム設定のアクセシビリティで許可してください"


def test_accessibility_permission_poll_interval_is_one_second() -> None:
    assert ACCESSIBILITY_PERMISSION_POLL_INTERVAL_MS == 1000


def test_accessibility_permission_status_returns_three_element_tuple() -> None:
    result_granted = accessibility_permission_status(True)
    result_denied = accessibility_permission_status(False)

    assert len(result_granted) == 3
    assert len(result_denied) == 3


def test_accessibility_permission_status_granted_has_no_help_text() -> None:
    _, _, help_text = accessibility_permission_status(True)

    assert help_text == ""


def test_accessibility_permission_status_denied_color_differs_from_granted() -> None:
    _, granted_color, _ = accessibility_permission_status(True)
    _, denied_color, _ = accessibility_permission_status(False)

    assert granted_color != denied_color
