#!/usr/bin/env bash
# Build the self-contained runtime bundled into the macOS app:
#   generated/runtime/python   standalone CPython 3.12 + service + mflux + ltx-2-mlx (no PyTorch)
#   generated/engines/         audiocpp_cli (+ VAD assets), llama-completion, sd-cli, ffmpeg
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/app/src-tauri/generated"
PY_SRC="$(uv python find 3.12)"                      # .../cpython-3.12.x/bin/python3.12
PY_HOME="$(cd "$(dirname "$(readlink -f "$PY_SRC")")/.." && pwd -P)"

rm -rf "$OUT/runtime" "$OUT/engines"
mkdir -p "$OUT/runtime" "$OUT/engines"

# 1. Private copy of the interpreter. Never install into the shared uv install.
cp -R "$PY_HOME/" "$OUT/runtime/python"
[ -L "$OUT/runtime/python" ] && { echo "runtime/python must not be a symlink" >&2; exit 1; }
PY="$OUT/runtime/python/bin/python3.12"
rm -f "$OUT/runtime/python/lib/python3.12/EXTERNALLY-MANAGED"
case "$(cd "$(dirname "$PY")" && pwd -P)" in "$OUT"/*) ;; *) echo "refusing to install outside $OUT" >&2; exit 1 ;; esac

PIP=(uv pip install -q --python "$PY" --break-system-packages --no-sources)
# Build real wheels: the ltx-2-mlx workspace would otherwise install its packages as
# editable links back into this checkout, which breaks on any other machine.
WHEELS="$OUT/.wheels"
rm -rf "$WHEELS"
for pkg in "$ROOT/service" "$ROOT/video/ltx-2-mlx/packages/ltx-core-mlx" "$ROOT/video/ltx-2-mlx/packages/ltx-pipelines-mlx"; do
  uv build -q --wheel --no-sources "$pkg" -o "$WHEELS"
done
"${PIP[@]}" "$WHEELS"/*.whl
rm -rf "$WHEELS"
# mflux declares torch/opencv/matplotlib, but the pre-converted MLX weights we ship do not need them.
"${PIP[@]}" --no-deps "mflux==0.20.0"
"${PIP[@]}" filelock fonttools "huggingface-hub>=1.1.6,<2" "mlx>=0.32.0,<0.33" "numpy>=2" piexif "pillow>=12.3" \
  platformdirs regex requests "safetensors>=0.4.4" sentencepiece toml tqdm "transformers>=5.5,<6" urllib3 protobuf pyyaml

# Trim what never runs in the app.
SP="$OUT/runtime/python/lib/python3.12"
rm -rf "$SP"/test "$SP"/idlelib "$SP"/tkinter "$SP"/turtledemo "$SP"/ensurepip "$SP"/site-packages/pip \
       "$OUT/runtime/python/lib/"libtcl* "$OUT/runtime/python/lib/"libtk* "$OUT/runtime/python/lib/"tcl* "$OUT/runtime/python/lib/"tk* \
       "$OUT/runtime/python/share" "$OUT/runtime/python/include"
find "$OUT/runtime" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$OUT/runtime" -path "*/site-packages/*/tests" -type d -prune -exec rm -rf {} +

# Precompile once so the app never writes __pycache__ inside its (signed) bundle.
"$PY" -m compileall -q -j 0 --invalidation-mode unchecked-hash "$SP" >/dev/null || true

# 2. Native engines.
AC="$ROOT/music/audio.cpp-latest"
mkdir -p "$OUT/engines/audiocpp/assets/framework/models"
cp "$AC/build/macos-metal-release/bin/audiocpp_cli" "$OUT/engines/audiocpp/"
cp -R "$AC/assets/framework/models/silero_vad" "$OUT/engines/audiocpp/assets/framework/models/"
cp "$ROOT/engines/llama.cpp/build-static/bin/llama-completion" "$OUT/engines/"
# stable-diffusion.cpp (Metal, statically linked): Qwen-Image 2.1 runs on it on the Mac too.
mkdir -p "$OUT/engines/sdcpp"
cp "$ROOT/image/stable-diffusion.cpp/build/bin/sd-cli" "$OUT/engines/sdcpp/"
FF="$("$PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"
if [ -z "$FF" ]; then
  "${PIP[@]}" imageio-ffmpeg
  FF="$("$PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
fi
cp "$FF" "$OUT/engines/ffmpeg"
"${PIP[@]}" >/dev/null 2>&1 || true
uv pip uninstall -q --python "$PY" --break-system-packages imageio-ffmpeg || true

# Fail the build if anything still points back into the development checkout.
if grep -rl "$ROOT" "$OUT/runtime/python/lib/python3.12/site-packages" --include="*.pth" --include="direct_url.json" 2>/dev/null \
   | xargs grep -l '"editable":true\|/src$' 2>/dev/null | grep -q .; then
  echo "editable install found in runtime" >&2; exit 1
fi
du -sh "$OUT/runtime" "$OUT/engines"
