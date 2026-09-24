"""Run a console-script entry point by name with the current interpreter.

The bundled runtime is relocatable, so the generated bin/ wrappers (which hard-code the
build machine's interpreter path) cannot be used. `python -m localai_service.entry
mflux-generate-z-image-turbo --prompt ...` resolves the entry point from package
metadata instead.
"""
import importlib.util
import sys
from importlib.metadata import entry_points
from pathlib import Path

SHIMS = Path(__file__).resolve().parent / "shims"


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m localai_service.entry <console-script> [args...]")
    name = sys.argv[1]
    matches = [ep for ep in entry_points(group="console_scripts") if ep.name == name]
    if not matches:
        raise SystemExit(f"unknown engine command: {name}")
    # Fall back to import placeholders only for libraries that are genuinely absent.
    if any(importlib.util.find_spec(m) is None for m in ("torch", "cv2")):
        sys.path.append(str(SHIMS))
    sys.argv = [name, *sys.argv[2:]]
    sys.exit(matches[0].load()())


if __name__ == "__main__":
    main()
