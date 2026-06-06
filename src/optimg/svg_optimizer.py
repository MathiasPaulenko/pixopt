"""SVG optimization in pure Python (no external Node.js tools required)."""

from __future__ import annotations

import re


def optimize_svg(data: str | bytes) -> str:
    """Minify an SVG by removing comments, redundant whitespace and default attributes.

    Args:
        data: Raw SVG content as str or bytes.

    Returns:
        Optimized SVG string.
    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    # Remove XML declaration
    data = re.sub(r'<\?xml[^?]*\?>', '', data)

    # Remove DOCTYPE
    data = re.sub(r'<!DOCTYPE[^>]*>', '', data, flags=re.IGNORECASE)

    # Remove HTML comments
    data = re.sub(r'<!--.*?-->', '', data, flags=re.DOTALL)

    # Remove CDATA sections (keep content)
    data = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', data, flags=re.DOTALL)

    # Normalize whitespace
    data = re.sub(r'\s+', ' ', data)

    # Remove spaces between tags
    data = re.sub(r'>\s+<', '><', data)

    # Remove leading/trailing spaces inside attributes
    data = re.sub(r'\s*=\s*', '=', data)

    # Remove empty attributes
    data = re.sub(r'\s+\w+=""', '', data)

    # Remove default attributes (common SVG defaults)
    defaults = [
        r'\s+fill="black"',
        r'\s+fill="#000000"',
        r'\s+fill="#000"',
        r'\s+stroke="none"',
        r'\s+stroke-width="1"',
        r'\s+opacity="1"',
        r'\s+fill-opacity="1"',
        r'\s+stroke-opacity="1"',
        r'\s+stroke-linecap="butt"',
        r'\s+stroke-linejoin="miter"',
        r'\s+stroke-miterlimit="4"',
        r'\s+stroke-dasharray="none"',
        r'\s+stroke-dashoffset="0"',
        r'\s+font-style="normal"',
        r'\s+font-weight="normal"',
        r'\s+text-anchor="start"',
    ]
    for pattern in defaults:
        data = re.sub(pattern, '', data, flags=re.IGNORECASE)

    # Round long decimals to 3 places
    def _round_decimals(match: re.Match[str]) -> str:
        num = match.group(0)
        try:
            rounded = round(float(num), 3)
            result = str(rounded).rstrip("0").rstrip(".")
            return result if result != "-0" else "0"
        except ValueError:
            return num

    data = re.sub(r'-?\d+\.\d{4,}', _round_decimals, data)

    # Remove unnecessary quotes around numeric attributes (safe subset)
    data = re.sub(r'(\w+)=\"(\d+(?:\.\d+)?)\"', r'\1=\2', data)

    return data.strip()
