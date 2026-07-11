import sys
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import accessibility_permission

mock = Mock()
sys.modules["pyautogui"] = mock

from status_window import (  # noqa: E402
    accessibility_permission_status,
    eb_lamp_colors,
    should_show_eb_lamp,
    should_show_accessibility_permission_status,
)
from mascon_controller import TrainProfile  # noqa: E402


def test_accessibility_permission_status_when_granted() -> None:
    text, color = accessibility_permission_status(True)

    assert text == "アクセシビリティ権限: 許可済み"
    assert color == "#57606a"


def test_accessibility_permission_status_when_denied() -> None:
    text, color = accessibility_permission_status(False)

    assert text == "アクセシビリティ権限: 未許可"
    assert color == "#b42318"


def test_eb_lamp_colors_when_off() -> None:
    background, foreground = eb_lamp_colors(False)

    assert background == "#ffffff"
    assert foreground == "#57606a"


def test_eb_lamp_colors_when_on() -> None:
    background, foreground = eb_lamp_colors(True)

    assert background == "#b42318"
    assert foreground == "#ffffff"


@pytest.mark.parametrize(
    ("profile", "requested", "expected"),
    [
        (TrainProfile.DEFAULT, False, False),
        (TrainProfile.DEFAULT, True, True),
        (TrainProfile.TOBU, True, False),
        (TrainProfile.SEIBU, True, False),
    ],
)
def test_should_show_eb_lamp(
    profile: TrainProfile,
    requested: bool,
    expected: bool,
) -> None:
    assert should_show_eb_lamp(profile, requested) is expected


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
