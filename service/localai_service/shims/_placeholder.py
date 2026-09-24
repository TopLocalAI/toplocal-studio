"""Import-time placeholders for heavy optional libraries the bundled engines never call.

mflux imports PyTorch (only for converting PyTorch-format checkpoints) and OpenCV (only
for ControlNet/OpenPose) at module level. The app ships pre-converted MLX weights and
does not use ControlNet, so these placeholders let the imports succeed; any real use
raises a clear error instead of silently misbehaving.
"""


class _Placeholder(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return make(f"{cls.__qualname__}.{name}")

    def __call__(cls, *args, **kwargs):
        raise RuntimeError(f"{cls.__qualname__} is not available in TopLocal Studio (library not bundled)")


def make(name: str) -> type:
    return _Placeholder(name, (), {"__qualname__": name})
