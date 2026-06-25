from types import ModuleType

from pytest_mock import MockerFixture

import accessibility_permission


def patch_platform(mocker: MockerFixture, platform: str) -> None:
    mocker.patch.object(accessibility_permission.sys, "platform", platform)


def fake_application_services(**attributes: object) -> ModuleType:
    module = ModuleType("ApplicationServices")
    for name, value in attributes.items():
        setattr(module, name, value)
    return module


def test_non_macos_treats_accessibility_permission_as_granted(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "linux")

    assert accessibility_permission.is_accessibility_permission_granted()


def test_macos_accessibility_permission_uses_application_services(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    mocker.patch.dict(
        "sys.modules",
        {
            "ApplicationServices": fake_application_services(
                AXIsProcessTrusted=lambda: True
            )
        },
    )

    assert accessibility_permission.is_accessibility_permission_granted()


def test_macos_accessibility_permission_returns_false_when_application_services_is_missing(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    mocker.patch.dict("sys.modules", {"ApplicationServices": None})

    assert not accessibility_permission.is_accessibility_permission_granted()


def test_macos_accessibility_permission_returns_false_when_call_fails(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    mocker.patch.dict(
        "sys.modules",
        {
            "ApplicationServices": fake_application_services(
                AXIsProcessTrusted=lambda: (_ for _ in ()).throw(
                    OSError("check failed")
                )
            )
        },
    )

    assert not accessibility_permission.is_accessibility_permission_granted()


def test_macos_accessibility_permission_returns_false_when_symbol_is_missing(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    mocker.patch.dict(
        "sys.modules",
        {"ApplicationServices": fake_application_services()},
    )

    assert not accessibility_permission.is_accessibility_permission_granted()


def test_prompt_for_accessibility_permission_skips_non_macos(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "linux")
    prompt_mock = mocker.patch(
        "accessibility_permission.prompt_for_macos_accessibility_permission"
    )

    accessibility_permission.prompt_for_accessibility_permission()

    prompt_mock.assert_not_called()


def test_prompt_for_accessibility_permission_skips_when_permission_is_granted(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    mocker.patch(
        "accessibility_permission.is_accessibility_permission_granted",
        return_value=True,
    )
    prompt_mock = mocker.patch(
        "accessibility_permission.prompt_for_macos_accessibility_permission"
    )

    accessibility_permission.prompt_for_accessibility_permission()

    prompt_mock.assert_not_called()


def test_prompt_for_accessibility_permission_prompts_when_permission_is_missing(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    mocker.patch(
        "accessibility_permission.is_accessibility_permission_granted",
        return_value=False,
    )
    prompt_mock = mocker.patch(
        "accessibility_permission.prompt_for_macos_accessibility_permission"
    )

    accessibility_permission.prompt_for_accessibility_permission()

    prompt_mock.assert_called_once_with()


def test_prompt_for_macos_accessibility_permission_returns_false_when_library_is_missing(
    mocker: MockerFixture,
) -> None:
    mocker.patch.dict("sys.modules", {"ApplicationServices": None})

    assert not accessibility_permission.prompt_for_macos_accessibility_permission()


def test_prompt_for_macos_accessibility_permission_uses_prompt_option(
    mocker: MockerFixture,
) -> None:
    prompt_calls: list[dict[str, bool]] = []

    def prompt_with_options(options: dict[str, bool]) -> bool:
        prompt_calls.append(options)
        return False

    mocker.patch.dict(
        "sys.modules",
        {
            "ApplicationServices": fake_application_services(
                AXIsProcessTrustedWithOptions=prompt_with_options,
                kAXTrustedCheckOptionPrompt="AXTrustedCheckOptionPrompt",
            )
        },
    )

    assert not accessibility_permission.prompt_for_macos_accessibility_permission()
    assert prompt_calls == [{"AXTrustedCheckOptionPrompt": True}]


def test_open_accessibility_settings_skips_non_macos(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "linux")
    run_mock = mocker.patch("accessibility_permission.subprocess.run")

    accessibility_permission.open_accessibility_settings()

    run_mock.assert_not_called()


def test_open_accessibility_settings_opens_macos_accessibility_settings(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    run_mock = mocker.patch("accessibility_permission.subprocess.run")

    accessibility_permission.open_accessibility_settings()

    run_mock.assert_called_once_with(
        ["open", accessibility_permission.ACCESSIBILITY_SETTINGS_URL],
        check=False,
    )


def test_open_accessibility_settings_ignores_open_failures(
    mocker: MockerFixture,
) -> None:
    patch_platform(mocker, "darwin")
    mocker.patch("accessibility_permission.subprocess.run", side_effect=OSError)

    accessibility_permission.open_accessibility_settings()
