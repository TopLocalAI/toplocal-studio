"""User settings persisted in DATA_DIR/settings.json."""
import json

from . import config

DEFAULTS = {"mirror": "huggingface", "hfToken": "", "language": "zh"}
LANGUAGES = ("zh", "en")
_PATH = config.DATA_DIR / "settings.json"


def load() -> dict:
    try:
        return {**DEFAULTS, **json.loads(_PATH.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def get(key: str):
    return load().get(key, DEFAULTS.get(key))


def update(values: dict) -> dict:
    data = load()
    if values.get("mirror") in ("huggingface", "hf-mirror"):
        data["mirror"] = values["mirror"]
    if values.get("language") in LANGUAGES:
        data["language"] = values["language"]
    if "hfToken" in values:
        data["hfToken"] = str(values["hfToken"]).strip()[:200]
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        _PATH.chmod(0o600)  # holds an access token
    except OSError:
        pass
    return data


def public() -> dict:
    data = load()
    return {"mirror": data["mirror"], "hasHfToken": bool(data["hfToken"]), "language": data["language"]}
