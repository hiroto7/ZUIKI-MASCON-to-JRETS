import sys
from argparse import Namespace
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

mock = Mock()
sys.modules["pyautogui"] = mock

import main  # noqa: E402
from mascon_controller import MasconController  # noqa: E402


def test_handle_pygame_events_uses_controller(
    mocker: MockerFixture,
) -> None:
    event = Mock()
    event.type = main.pygame.JOYAXISMOTION
    event.dict = {"value": 1.0}
    mocker.patch("main.pygame.event.get", return_value=[event])
    controller = MasconController()
    handle_axis_motion_mock = mocker.patch.object(controller, "handle_axis_motion")

    main.handle_pygame_events(controller, Namespace(verbose=False))

    handle_axis_motion_mock.assert_called_once_with(1.0)


def test_warn_if_accessibility_permission_is_missing_outputs_warning(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    mocker.patch("main.is_macos", return_value=True)
    mocker.patch("main.is_accessibility_permission_granted", return_value=False)

    main.warn_if_accessibility_permission_is_missing()

    captured = capsys.readouterr()
    assert "アクセシビリティ権限が未許可です" in captured.err
    assert captured.out == ""


def test_warn_if_accessibility_permission_is_missing_skips_non_macos(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    mocker.patch("main.is_macos", return_value=False)
    permission_mock = mocker.patch("main.is_accessibility_permission_granted")

    main.warn_if_accessibility_permission_is_missing()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""
    permission_mock.assert_not_called()


def test_main_starts_status_window(
    mocker: MockerFixture,
) -> None:
    args = Namespace(profile="default", verbose=False)
    mocker.patch("main.parse_args", return_value=args)
    prompt_mock = mocker.patch("main.prompt_for_accessibility_permission")
    warn_mock = mocker.patch("main.warn_if_accessibility_permission_is_missing")
    status_window_mock = mocker.patch("main.StatusWindow")
    initialize_mock = mocker.patch("main.initialize_pygame")

    main.main()

    prompt_mock.assert_called_once_with()
    warn_mock.assert_called_once_with()
    status_window_mock.assert_called_once()
    controller = status_window_mock.call_args.args[0]
    assert isinstance(controller, MasconController)
    assert controller.profile == main.TrainProfile.DEFAULT
    initialize_mock.assert_called_once_with(controller)
    status_window_mock.return_value.run.assert_called_once_with()


def test_initialize_pygame_uses_dummy_video_driver(
    mocker: MockerFixture,
) -> None:
    controller = MasconController()
    mocker.patch("main.pygame.init")
    mocker.patch("main.pygame.display.set_allow_screensaver")
    initialize_joysticks_mock = mocker.patch.object(controller, "initialize_joysticks")
    mocker.patch.dict(main.os.environ, {}, clear=True)

    main.initialize_pygame(controller)

    assert main.os.environ["SDL_VIDEODRIVER"] == "dummy"
    initialize_joysticks_mock.assert_called_once_with()
