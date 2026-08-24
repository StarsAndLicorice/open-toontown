#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_tree=${PANDA3D_SOURCE:-"$repo_root/../panda3d"}
build_source="$repo_root/local/panda3d-wheel-source"
build_output="$repo_root/local/panda3d-build"

if [ ! -f "$source_tree/makepanda/makepanda.py" ]; then
  echo "Panda3D source not found at $source_tree" >&2
  echo "Set PANDA3D_SOURCE if it is stored somewhere else." >&2
  exit 1
fi

if [ ! -x "$repo_root/.venv/bin/python" ]; then
  python -m venv "$repo_root/.venv"
  "$repo_root/.venv/bin/python" -m pip install -r "$repo_root/requirements.txt"
fi

mkdir -p "$repo_root/local"
if [ ! -d "$build_source" ]; then
  cp -a "$source_tree" "$build_source"
  patch -d "$build_source" -p1 < "$repo_root/nix/panda3d-nix-wheel.patch"
fi
mkdir -p "$build_output"

cd "$build_source"
"$repo_root/.venv/bin/python" makepanda/makepanda.py \
  --everything \
  --wheel \
  --outputdir "$build_output" \
  --threads "${PANDA3D_BUILD_THREADS:-8}" \
  --no-egl --no-gles --no-gles2 --no-opencv \
  --python-incdir "$PANDA_PYTHON_INCDIR" \
  --python-libdir "$PANDA_PYTHON_LIBDIR"

wheel=$(find "$build_source" -maxdepth 1 -name 'panda3d-*.whl' -print -quit)
if [ -z "$wheel" ]; then
  echo "Panda3D build completed without producing a wheel" >&2
  exit 1
fi

"$repo_root/.venv/bin/python" -m pip install --force-reinstall "$wheel"
"$repo_root/.venv/bin/python" -c \
  'import panda3d.core, panda3d.otp, panda3d.toontown; print("Installed Panda3D", panda3d.core.PandaSystem.get_version_string())'
