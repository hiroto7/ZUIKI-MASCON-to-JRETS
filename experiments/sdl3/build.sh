#!/usr/bin/env bash
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'This experiment requires macOS.' >&2; exit 1; }
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
export ZUIKI_SDL3_ROOT="${ZUIKI_SDL3_ROOT:-$SCRIPT_DIR/../../build/sdl3-experiment}"
mkdir -p "$ZUIKI_SDL3_ROOT"
ZUIKI_SDL3_ROOT="$(cd "$ZUIKI_SDL3_ROOT" && pwd)"
export ZUIKI_SDL3_ROOT
cd "$ZUIKI_SDL3_ROOT"
SDL_VERSION=3.4.16
PYGAME_COMMIT=f2e3f55e5f84a56044583e0e147618a06ef7ddb7
curl --fail --location --silent --show-error "https://github.com/libsdl-org/SDL/releases/download/release-$SDL_VERSION/SDL3-$SDL_VERSION.tar.gz" -o SDL3.tar.gz
echo '7322236cd12090c3eb40b9728be4d49c76f66ad17d04369584d4ecad5cf77c68  SDL3.tar.gz' | shasum -a 256 -c -
tar -xzf SDL3.tar.gz
uv run --isolated --no-project --with cmake==4.1.0 cmake -S "SDL3-$SDL_VERSION" -B sdl-build -DSDL_TESTS=OFF -DSDL_STATIC=OFF -DCMAKE_BUILD_TYPE=Release
uv run --isolated --no-project --with cmake==4.1.0 cmake --build sdl-build --parallel 8
uv run --isolated --no-project --with cmake==4.1.0 cmake --install sdl-build --prefix "$ZUIKI_SDL3_ROOT/prefix"
if [[ ! -d pygame-ce ]]; then
    git clone https://github.com/pygame-community/pygame-ce.git pygame-ce
fi
# This checkout is reserved for the experiment. Only our known patch is reapplied.
git -C pygame-ce checkout "$PYGAME_COMMIT"
uv venv --python 3.13 --allow-existing env
"env/bin/python" "$SCRIPT_DIR/patch_build.py" pygame-ce/src_c/meson.build
CMAKE_PREFIX_PATH="$ZUIKI_SDL3_ROOT/prefix" uv run --isolated --no-project --with cmake==4.1.0 uv pip install \
    --python env/bin/python ./pygame-ce \
    -Csetup-args=-Dsdl_api=3 -Csetup-args=-Dimage=disabled \
    -Csetup-args=-Dmixer=disabled -Csetup-args=-Dfont=disabled \
    -Csetup-args=-Dfreetype=disabled -Csetup-args=-Dmidi=disabled \
    pyautogui==0.9.54 pyobjc-framework-applicationservices==12.2.2
"env/bin/python" -c 'import pygame; print("pygame-ce", pygame.version.ver, "SDL", pygame.get_sdl_version()); assert pygame.get_sdl_version()[0] == 3'
