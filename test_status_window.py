import threading
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from mascon_controller import (
    DpadButton,
    MasconController,
    Notch,
    TrainProfile,
    ZuikiMasconButton,
)
from status_window import StatusApi, StatusWindow, build_status_snapshot


def test_build_status_snapshot_contains_controller_state(
    mocker: MockerFixture,
) -> None:
    mocker.patch("status_window.is_macos", return_value=True)
    mocker.patch(
        "status_window.is_accessibility_permission_granted", return_value=False
    )
    controller = MasconController(
        profile=TrainProfile.TOBU,
        raw_notch=Notch.P5,
        pressed_buttons={ZuikiMasconButton.A, DpadButton.LEFT},
        joysticks={1: Mock()},
    )

    status = build_status_snapshot(controller)

    assert status["notch"] == "P3"
    assert status["raw_notch"] == "P5"
    assert status["profile"] == "tobu"
    assert status["max_power"] == "P3"
    assert status["max_brake"] == "B7"
    assert status["controller_count"] == 1
    assert status["pressed_buttons"] == ["A", "LEFT"]
    assert status["show_accessibility"] is True
    assert status["accessibility_granted"] is False
    assert next(item for item in status["profiles"] if item["id"] == "tobu")["selected"]


def test_build_status_snapshot_hides_accessibility_status_on_linux(
    mocker: MockerFixture,
) -> None:
    mocker.patch("status_window.is_macos", return_value=False)
    permission_mock = mocker.patch("status_window.is_accessibility_permission_granted")

    status = build_status_snapshot(MasconController())

    assert status["show_accessibility"] is False
    assert status["accessibility_granted"] is True
    permission_mock.assert_not_called()


def test_status_api_changes_profile() -> None:
    controller = MasconController()
    api = StatusApi(controller)

    status = api.change_profile("seibu")

    assert controller.profile == TrainProfile.SEIBU
    assert status["profile"] == "seibu"


def test_status_api_rejects_unknown_profile() -> None:
    api = StatusApi(MasconController())

    with pytest.raises(ValueError, match="Unknown train profile"):
        api.change_profile("unknown")


def test_status_window_close_releases_inputs_once(
    mocker: MockerFixture,
) -> None:
    pygame_quit_mock = mocker.patch("status_window.pygame.quit")
    controller = MasconController()
    release_mock = mocker.patch.object(controller, "release_all_inputs")
    status_window = object.__new__(StatusWindow)
    status_window.controller = controller
    status_window.stop_event = threading.Event()
    status_window.controller_lock = threading.RLock()

    status_window.close()
    status_window.close()

    release_mock.assert_called_once_with()
    pygame_quit_mock.assert_called_once_with()
