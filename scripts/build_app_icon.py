import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


ICON_SIZES = (
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def render_svg_to_png(svg_path: Path, output_dir: Path) -> Path:
    run(["qlmanage", "-t", "-s", "1024", "-o", str(output_dir), str(svg_path)])
    rendered_path = output_dir / f"{svg_path.name}.png"
    if not rendered_path.exists():
        raise FileNotFoundError(f"Rendered PNG was not created: {rendered_path}")
    return rendered_path


def create_iconset(base_png: Path, iconset_dir: Path) -> None:
    iconset_dir.mkdir(parents=True, exist_ok=True)
    for filename, size in ICON_SIZES:
        output_path = iconset_dir / filename
        if size == 1024:
            shutil.copyfile(base_png, output_path)
        else:
            run(
                [
                    "sips",
                    "-z",
                    str(size),
                    str(size),
                    str(base_png),
                    "--out",
                    str(output_path),
                ]
            )


def build_icns(svg_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zuiki-app-icon-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        rendered_png = render_svg_to_png(svg_path, temp_dir)
        iconset_dir = temp_dir / "app-icon.iconset"
        create_iconset(rendered_png, iconset_dir)
        run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_path)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", type=Path, default=Path("assets/app-icon.svg"))
    parser.add_argument("--out", type=Path, default=Path("build/app-icon.icns"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_icns(args.svg, args.out)


if __name__ == "__main__":
    main()
