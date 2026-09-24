"""User-facing service messages in the UI language.

Source strings are the Chinese texts used throughout the code; `tr` looks up the English
version when the UI language (a user setting) is English. Placeholders use str.format
names: tr("需要约 {size} GB", size=3.2).
"""
from . import settings
from .i18n_en import EN


def language() -> str:
    return settings.get("language") or "zh"


def tr(source: str, /, **values) -> str:
    # `source` is positional-only so a placeholder may itself be called "text".
    if language() == "en":
        source = EN.get(source, source)
    return source.format(**values) if values else source
