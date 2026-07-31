"""Predefined and user-defined optimization presets/profiles.

A *preset* is a named bundle of optimization parameters that can be applied
with a single ``--preset`` flag on the CLI or via the ``apply_preset()``
helper from the library.

Built-in presets
----------------
- ``web``        – balanced JPEG/WEBP for general web use.
- ``social``     – square crop, high quality for social media.
- ``thumbnail``  – small thumbnails, aggressive compression.
- ``e-commerce`` – high quality, preserved metadata for product images.
- ``print``      – lossless, high resolution, metadata kept.

Custom presets
--------------
Users can define their own presets in a JSON file and pass it via
``--preset-file path/to/presets.json``.  Each key is the preset name and
the value is a dict of optimization parameters (same names as the CLI
options, using dashes).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from pixopt._units import (
    MAX_IMAGE_DIMENSION,
    MAX_PRESET_FILE_SIZE_BYTES,
    MAX_QUALITY,
    MIN_QUALITY,
)
from pixopt.utils import validate_no_parent_references

__all__ = [
    "BUILTIN_PRESETS",
    "apply_preset",
    "get_preset_names",
    "load_custom_presets",
    "resolve_preset",
]

# ---------------------------------------------------------------------------
# Built-in presets
# ---------------------------------------------------------------------------

BUILTIN_PRESETS: dict[str, dict[str, Any]] = {
    "web": {
        "quality": 80,
        "strip": True,
        "progressive": True,
        "optimize": True,
        "fit": "cover",
        "max-width": 1920,
        "max-height": 1080,
        "auto-orient": True,
    },
    "social": {
        "quality": 90,
        "strip": True,
        "progressive": True,
        "optimize": True,
        "fit": "cover",
        "aspect-ratio": "1:1",
        "max-width": 1200,
        "max-height": 1200,
        "anchor": "center",
        "auto-orient": True,
    },
    "thumbnail": {
        "quality": 70,
        "strip": True,
        "progressive": True,
        "optimize": True,
        "fit": "cover",
        "max-width": 300,
        "max-height": 300,
        "auto-orient": True,
    },
    "e-commerce": {
        "quality": 92,
        "strip": False,
        "progressive": True,
        "optimize": True,
        "fit": "contain",
        "max-width": 2000,
        "max-height": 2000,
        "background-color": "#ffffff",
        "auto-orient": True,
    },
    "print": {
        "quality": 100,
        "strip": False,
        "progressive": False,
        "optimize": True,
        "lossless": True,
        "auto-orient": True,
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Keys that the CLI/optimizer recognise.  We keep this list explicit so
# that unknown keys raise a clear error instead of being silently ignored.
_VALID_KEYS: frozenset[str] = frozenset(
    {
        "quality",
        "strip",
        "progressive",
        "optimize",
        "lossless",
        "fit",
        "anchor",
        "aspect-ratio",
        "background-color",
        "auto-orient",
        "max-width",
        "max-height",
        "format",
        "target-size",
        "min-size",
        "smart-format",
    }
)

# Bounds for numeric preset values so a malicious or malformed preset cannot
# request enormous resources (e.g., 9999999999px images).
_PRESET_BOUNDS: dict[str, tuple[int | None, int | None]] = {
    "quality": (MIN_QUALITY, MAX_QUALITY),
    "max-width": (1, MAX_IMAGE_DIMENSION),
    "max-height": (1, MAX_IMAGE_DIMENSION),
    "target-size": (1, None),
    "min-size": (0, None),
}

_BOOLEAN_KEYS: frozenset[str] = frozenset(
    {
        "strip",
        "progressive",
        "optimize",
        "lossless",
        "auto-orient",
        "smart-format",
    }
)


def _validate_preset_params(name: str, params: dict[str, Any]) -> None:
    """Validate the values inside a single preset definition."""
    for key, value in params.items():
        if key in _BOOLEAN_KEYS and not isinstance(value, bool):
            raise ValueError(
                f"Preset '{name}' key '{key}' must be a boolean, got {type(value).__name__}"
            )

        if key == "aspect-ratio":
            from pixopt.image_ops import parse_aspect_ratio

            if not isinstance(value, str):
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be a string, got {type(value).__name__}"
                )
            parse_aspect_ratio(value)

        if key == "fit":
            from pixopt.models import FitMode

            if not isinstance(value, str):
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be a string, got {type(value).__name__}"
                )
            try:
                FitMode(value)
            except ValueError as exc:
                raise ValueError(f"Preset '{name}' key '{key}' has invalid value: {value}") from exc

        if key == "anchor":
            from pixopt.models import Anchor

            if not isinstance(value, str):
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be a string, got {type(value).__name__}"
                )
            try:
                Anchor(value)
            except ValueError as exc:
                raise ValueError(f"Preset '{name}' key '{key}' has invalid value: {value}") from exc

        if key == "background-color":
            from pixopt.image_ops import parse_color

            if not isinstance(value, str):
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be a string, got {type(value).__name__}"
                )
            try:
                parse_color(value)
            except ValueError as exc:
                raise ValueError(f"Preset '{name}' key '{key}' has invalid value: {value}") from exc

        if key == "format":
            from pixopt.models import OutputFormat

            if not isinstance(value, str):
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be a string, got {type(value).__name__}"
                )
            try:
                OutputFormat(value.lower())
            except ValueError as exc:
                raise ValueError(f"Preset '{name}' key '{key}' has invalid value: {value}") from exc

        if key in _PRESET_BOUNDS:
            lower, upper = _PRESET_BOUNDS[key]
            if not isinstance(value, int):
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be an integer, got {type(value).__name__}"
                )
            if lower is not None and value < lower:
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be at least {lower}, got {value}"
                )
            if upper is not None and value > upper:
                raise ValueError(
                    f"Preset '{name}' key '{key}' must be at most {upper}, got {value}"
                )


def get_preset_names() -> list[str]:
    """Return the names of all built-in presets."""
    return sorted(BUILTIN_PRESETS)


def load_custom_presets(path: Path | str) -> dict[str, dict[str, Any]]:
    """Load user-defined presets from a JSON file.

    The file must contain a JSON object whose keys are preset names and
    whose values are dicts of optimization parameters.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file is not valid JSON or contains invalid keys.
    """
    p = Path(path)
    if error := validate_no_parent_references(p, "path"):
        raise ValueError(error)
    try:
        stat = p.stat()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Preset file not found: {p}") from exc

    if stat.st_size > MAX_PRESET_FILE_SIZE_BYTES:
        raise ValueError(f"Preset file too large (max {MAX_PRESET_FILE_SIZE_BYTES} bytes)")

    raw = p.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in preset file {p}: {exc}"
        raise ValueError(msg) from exc

    if not isinstance(data, dict):
        msg = f"Preset file must contain a JSON object, got {type(data).__name__}"
        raise ValueError(msg)

    for name, params in data.items():
        if not isinstance(params, dict):
            msg = f"Preset '{name}' must be a dict, got {type(params).__name__}"
            raise ValueError(msg)
        invalid = set(params) - _VALID_KEYS
        if invalid:
            msg = (
                f"Preset '{name}' contains unknown keys: "
                f"{', '.join(sorted(invalid))}. "
                f"Valid keys: {', '.join(sorted(_VALID_KEYS))}"
            )
            raise ValueError(msg)
        _validate_preset_params(name, params)

    return data


def resolve_preset(
    name: str,
    custom_presets: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a copy of the preset named *name*.

    Custom presets take precedence over built-ins.

    Raises:
        KeyError: If *name* is not a known preset.
    """
    if custom_presets and name in custom_presets:
        return deepcopy(custom_presets[name])
    if name in BUILTIN_PRESETS:
        return deepcopy(BUILTIN_PRESETS[name])
    available = ", ".join(get_preset_names())
    msg = f"Unknown preset '{name}'. Available: {available}"
    raise KeyError(msg)


def apply_preset(
    name: str,
    custom_presets: dict[str, dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Resolve *name* and merge *overrides* on top.

    Explicit CLI arguments always win over preset values.
    Returns a flat dict ready to be unpacked as ``optimize_image`` kwargs
    or forwarded to the CLI command.
    """
    params = resolve_preset(name, custom_presets)
    params.update(overrides)
    return params
