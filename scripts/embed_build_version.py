import os
import re
from pathlib import Path


def build_ci_label(ref: str, sha: str) -> str:
    return f"{ref} ({sha[:7]})"


def update_build_label(content: str, label: str) -> str:
    updated, count = re.subn(
        r"^BUILD_LABEL = .*$",
        f"BUILD_LABEL = {label!r}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("Could not update BUILD_LABEL")

    return updated


def main() -> None:
    path = Path("version_info.py")
    label = build_ci_label(os.environ["BUILD_REF"], os.environ["BUILD_SHA"])
    path.write_text(update_build_label(path.read_text(), label))


if __name__ == "__main__":
    main()
