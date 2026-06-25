import sys
import subprocess

ACCESSIBILITY_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_accessibility_permission_granted() -> bool:
    if not is_macos():
        return True

    return is_macos_accessibility_permission_granted()


def prompt_for_accessibility_permission() -> None:
    if not is_macos() or is_accessibility_permission_granted():
        return

    prompt_for_macos_accessibility_permission()


def is_macos_accessibility_permission_granted() -> bool:
    try:
        # Import inside the macOS-only path so Linux can load this module.
        # The local stub covers types; Linux CI lacks the runtime package source.
        from ApplicationServices import (  # pyright: ignore[reportMissingModuleSource]
            AXIsProcessTrusted,
        )

        return bool(AXIsProcessTrusted())
    except (ImportError, OSError, AttributeError, TypeError):
        return False


def prompt_for_macos_accessibility_permission() -> bool:
    try:
        # Import inside the macOS-only path so Linux can load this module.
        # The local stub covers types; Linux CI lacks the runtime package source.
        from ApplicationServices import (  # pyright: ignore[reportMissingModuleSource]
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )

        return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
    except (ImportError, OSError, AttributeError, TypeError):
        return False


def open_accessibility_settings() -> None:
    if not is_macos():
        return

    try:
        subprocess.run(["open", ACCESSIBILITY_SETTINGS_URL], check=False)
    except OSError:
        pass
