import sys
from argparse import Namespace
from unittest.mock import Mock

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
