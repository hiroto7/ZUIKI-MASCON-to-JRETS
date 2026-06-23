from collections.abc import Callable
from ctypes import c_bool

from pytest_mock import MockerFixture

import accessibility_permission


class FakeAXIsProcessTrusted:
    def __init__(self, trusted: bool) -> None:
        self.trusted = trusted
        self.argtypes: list[object] | None = None
        self.restype: object | None = None

    def __call__(self) -> bool:
        return self.trusted


class FakeApplicationServices:
    def __init__(self, trusted: bool) -> None:
        self.AXIsProcessTrusted = FakeAXIsProcessTrusted(trusted)


def patch_platform(mocker: MockerFixture, platform: str) -> None:
    mocker.patch.object(accessibility_permission.sys, "platform", platform)


def test_non_macos_treats_accessibility_permission_as_granted(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "linux")

    assert accessibility_permission.is_accessibility_permission_granted()


def test_macos_accessibility_permission_uses_application_services(
    mocker: MockerFixture,
) -> None:
    fake_application_services = FakeApplicationServices(True)
    patch_platform(mocker, "darwin")
    mocker.patch("accessibility_permission.find_library", return_value="app-services")
    mocker.patch(
        "accessibility_permission.CDLL", return_value=fake_application_services
    )

    assert accessibility_permission.is_accessibility_permission_granted()
    assert fake_application_services.AXIsProcessTrusted.argtypes == []
    assert fake_application_services.AXIsProcessTrusted.restype == c_bool


def test_macos_accessibility_permission_returns_false_when_library_is_missing(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    cdll_mock: Callable[[str], object] = mocker.patch("accessibility_permission.CDLL")
    mocker.patch("accessibility_permission.find_library", return_value=None)

    assert not accessibility_permission.is_accessibility_permission_granted()
    cdll_mock.assert_not_called()


def test_is_macos_returns_true_on_darwin(mocker: MockerFixture) -> None:
    patch_platform(mocker, "darwin")

    assert accessibility_permission.is_macos() is True


def test_is_macos_returns_false_on_linux(mocker: MockerFixture) -> None:
    patch_platform(mocker, "linux")

    assert accessibility_permission.is_macos() is False


def test_is_macos_returns_false_on_windows(mocker: MockerFixture) -> None:
    patch_platform(mocker, "win32")

    assert accessibility_permission.is_macos() is False


def test_macos_accessibility_permission_denied_via_application_services(
    mocker: MockerFixture,
) -> None:
    fake_application_services = FakeApplicationServices(False)
    patch_platform(mocker, "darwin")
    mocker.patch("accessibility_permission.find_library", return_value="app-services")
    mocker.patch(
        "accessibility_permission.CDLL", return_value=fake_application_services
    )

    assert not accessibility_permission.is_accessibility_permission_granted()


def test_is_macos_accessibility_permission_granted_returns_false_when_not_trusted(
    mocker: MockerFixture,
) -> None:
    fake_application_services = FakeApplicationServices(False)
    mocker.patch("accessibility_permission.find_library", return_value="app-services")
    mocker.patch(
        "accessibility_permission.CDLL", return_value=fake_application_services
    )

    assert not accessibility_permission.is_macos_accessibility_permission_granted()


def test_is_macos_accessibility_permission_granted_returns_true_when_trusted(
    mocker: MockerFixture,
) -> None:
    fake_application_services = FakeApplicationServices(True)
    mocker.patch("accessibility_permission.find_library", return_value="app-services")
    mocker.patch(
        "accessibility_permission.CDLL", return_value=fake_application_services
    )

    assert accessibility_permission.is_macos_accessibility_permission_granted()
