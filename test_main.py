import sys
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture

mock = Mock()
sys.modules["pyautogui"] = mock

from main import Notch, get_notch, update_notch


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
    ("current", "next", "calls"),
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
        pytest.param(Notch.EB, Notch.B5, [call(",", 4)], id="EB -> B5"),
    ],
)
def test_update_notch(
    mocker: MockerFixture, current: Notch, next: Notch, calls: list[object]
) -> None:
    press_mock = mocker.patch("main.press")
    update_notch(current, next)
    assert press_mock.call_args_list == calls
