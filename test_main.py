import sys
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture

mock = Mock()
sys.modules["pyautogui"] = mock

from main import (
    Notch,
    PROFILE_LIMITS,
    TrainProfile,
    get_notch,
    mouse_y_to_mascon_value,
    project_notch,
    update_notch,
)


def test_get_notch() -> None:
    assert get_notch(1.0, False) == Notch.P5
    assert get_notch(0.8039185766167181, False) == Notch.P4
    assert get_notch(0.6156804101687674, False) == Notch.P3
    assert get_notch(0.43528550065614796, False) == Notch.P2
    assert get_notch(0.24704733420819727, False) == Notch.P1
    assert get_notch(0.003906369212927641, False) == Notch.N
    assert get_notch(-0.20786156804101688, False) == Notch.B1
    assert get_notch(-0.3176671651356548, False) == Notch.B2
    assert get_notch(-0.4274727622302927, False) == Notch.B3
    assert get_notch(-0.5294351023895993, False) == Notch.B4
    assert get_notch(-0.6392406994842372, False) == Notch.B5
    assert get_notch(-0.7490462965788751, False) == Notch.B6
    assert get_notch(-0.8510086367381817, False) == Notch.B7
    assert get_notch(-0.9608142338328196, False) == Notch.B8
    assert get_notch(-1.000030518509476, True) == Notch.EB


@pytest.mark.parametrize(
    ("mouse_y", "height", "expected"),
    [
        pytest.param(0, 400, 1.0, id="top edge"),
        pytest.param(200, 400, 0.0, id="center"),
        pytest.param(400, 400, -1.0, id="bottom edge"),
        pytest.param(-100, 400, 1.0, id="above window clamps to power max"),
        pytest.param(500, 400, -1.0, id="below window clamps to brake max"),
    ],
)
def test_mouse_y_to_mascon_value(mouse_y: int, height: int, expected: float) -> None:
    assert mouse_y_to_mascon_value(mouse_y, height) == expected


@pytest.mark.parametrize(
    ("current", "next_notch", "calls"),
    [
        pytest.param(Notch.P2, Notch.P5, [call("z", 3)], id="P2 -> P5"),
        pytest.param(Notch.P2, Notch.P1, [call("a", 1)], id="P2 -> P1"),
        pytest.param(Notch.P2, Notch.N, [call("s")], id="P2 -> N"),
        pytest.param(Notch.P2, Notch.B5, [call("s"), call(".", 5)], id="P2 -> B5"),
        pytest.param(Notch.P2, Notch.EB, [call("s"), call("/")], id="P2 -> EB"),
        pytest.param(Notch.N, Notch.P2, [call("z", 2)], id="N -> P2"),
        pytest.param(Notch.N, Notch.B5, [call(".", 5)], id="N -> B5"),
        pytest.param(Notch.N, Notch.EB, [call("/")], id="N -> EB"),
        pytest.param(Notch.B5, Notch.P2, [call("m"), call("z", 2)], id="B5 -> P2"),
        pytest.param(Notch.B5, Notch.N, [call("m")], id="B5 -> N"),
        pytest.param(Notch.B5, Notch.B1, [call(",", 4)], id="B5 -> B1"),
        pytest.param(Notch.B5, Notch.B8, [call(".", 3)], id="B5 -> B8"),
        pytest.param(Notch.B5, Notch.EB, [call("/")], id="B5 -> EB"),
        pytest.param(Notch.EB, Notch.P2, [call("m"), call("z", 2)], id="EB -> P2"),
        pytest.param(Notch.EB, Notch.N, [call("m")], id="EB -> N"),
    ],
)
def test_update_notch(
    mocker: MockerFixture, current: Notch, next_notch: Notch, calls: list[object]
) -> None:
    press_mock = mocker.patch("main.press")
    update_notch(current, next_notch, Notch.B8)
    assert press_mock.call_args_list == calls


@pytest.mark.parametrize(
    "notch",
    [Notch.P2, Notch.N, Notch.B5, Notch.EB],
)
def test_update_notch_does_nothing_when_notch_is_unchanged(
    mocker: MockerFixture, notch: Notch
) -> None:
    press_mock = mocker.patch("main.press")
    update_notch(notch, notch, Notch.B8)
    press_mock.assert_not_called()


@pytest.mark.parametrize(
    ("profile", "current", "next_notch", "calls"),
    [
        pytest.param(
            TrainProfile.DEFAULT,
            Notch.EB,
            Notch.B8,
            [call(",", 1)],
            id="default EB -> B8",
        ),
        pytest.param(
            TrainProfile.DEFAULT,
            Notch.EB,
            Notch.B5,
            [call(",", 4)],
            id="default EB -> B5",
        ),
        pytest.param(
            TrainProfile.TOBU,
            Notch.EB,
            Notch.B7,
            [call(",", 1)],
            id="tobu EB -> B7",
        ),
        pytest.param(
            TrainProfile.TOBU,
            Notch.EB,
            Notch.B5,
            [call(",", 3)],
            id="tobu EB -> B5",
        ),
    ],
)
def test_update_notch_from_emergency_brake_uses_profile_brake_order(
    mocker: MockerFixture,
    profile: TrainProfile,
    current: Notch,
    next_notch: Notch,
    calls: list[object],
) -> None:
    press_mock = mocker.patch("main.press")
    update_notch(current, next_notch, PROFILE_LIMITS[profile].max_brake)
    assert press_mock.call_args_list == calls


@pytest.mark.parametrize(
    ("profile", "raw_notch", "expected"),
    [
        pytest.param(
            TrainProfile.DEFAULT,
            Notch.P5,
            Notch.P5,
            id="default P5 -> P5",
        ),
        pytest.param(
            TrainProfile.DEFAULT,
            Notch.B8,
            Notch.B8,
            id="default B8 -> B8",
        ),
        pytest.param(TrainProfile.TOBU, Notch.P5, Notch.P3, id="tobu P5 -> P3"),
        pytest.param(TrainProfile.TOBU, Notch.P4, Notch.P3, id="tobu P4 -> P3"),
        pytest.param(TrainProfile.TOBU, Notch.P3, Notch.P3, id="tobu P3 -> P3"),
        pytest.param(TrainProfile.TOBU, Notch.B8, Notch.B7, id="tobu B8 -> B7"),
        pytest.param(TrainProfile.TOBU, Notch.B7, Notch.B7, id="tobu B7 -> B7"),
        pytest.param(TrainProfile.SEIBU, Notch.P5, Notch.P4, id="seibu P5 -> P4"),
        pytest.param(TrainProfile.SEIBU, Notch.P4, Notch.P4, id="seibu P4 -> P4"),
        pytest.param(TrainProfile.SEIBU, Notch.B8, Notch.B7, id="seibu B8 -> B7"),
        pytest.param(TrainProfile.SEIBU, Notch.B7, Notch.B7, id="seibu B7 -> B7"),
    ],
)
def test_project_notch_applies_profile_limits(
    profile: TrainProfile, raw_notch: Notch, expected: Notch
) -> None:
    assert project_notch(raw_notch, PROFILE_LIMITS[profile]) == expected


@pytest.mark.parametrize("profile", list(TrainProfile))
def test_project_notch_keeps_emergency_brake(profile: TrainProfile) -> None:
    assert project_notch(Notch.EB, PROFILE_LIMITS[profile]) == Notch.EB
