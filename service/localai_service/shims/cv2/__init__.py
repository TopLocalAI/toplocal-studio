from localai_service.shims._placeholder import make as _make

__version__ = "0+placeholder"


def __getattr__(name):
    if name.startswith("__"):
        raise AttributeError(name)
    return _make("cv2." + name)
