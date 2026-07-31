"""Shared helpers for CLI preset handling."""

from __future__ import annotations

from typing import Any

from pixopt.presets import load_custom_presets


def merge_preset(
    preset_name: str | None,
    preset_file: str | None,
    explicit: dict[str, Any],
) -> dict[str, Any]:
    """Merge a named preset with explicitly-provided CLI arguments.

    *explicit* maps CLI option names (with dashes) to values that were
    actually provided by the user.  ``None`` values mean "not provided"
    and are replaced by the preset value when a preset is active.

    Returns a dict with the same keys, ready to be unpacked into the
    optimizer / command call.
    """
    if preset_name is None:
        return {k: v for k, v in explicit.items() if v is not None}

    custom = load_custom_presets(preset_file) if preset_file else None
    from pixopt.presets import resolve_preset

    base = resolve_preset(preset_name, custom)

    merged: dict[str, Any] = {}
    for key, value in explicit.items():
        if value is not None:
            merged[key] = value
        elif key in base:
            merged[key] = base[key]
    return merged
