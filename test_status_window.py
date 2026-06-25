import sys
from unittest.mock import Mock

from pytest_mock import MockerFixture

import accessibility_permission

mock = Mock()
sys.modules["pyautogui"] = mock

from status_window import (  # noqa: E402
    accessibility_permission_status,
    should_show_accessibility_permission_status,
)


def test_accessibility_permission_status_when_granted() -> None:
    text, color = accessibility_permission_status(True)

    assert text == "アクセシビリティ権限: 許可済み"
    assert color == "#57606a"


def test_accessibility_permission_status_when_denied() -> None:
    text, color = accessibility_permission_status(False)

    assert text == "アクセシビリティ権限: 未許可"
    assert color == "#b42318"


def test_should_show_accessibility_permission_status_on_macos(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(accessibility_permission.sys, "platform", "darwin")

    assert should_show_accessibility_permission_status()


def test_should_hide_accessibility_permission_status_on_non_macos(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(accessibility_permission.sys, "platform", "linux")

    assert not should_show_accessibility_permission_status()
