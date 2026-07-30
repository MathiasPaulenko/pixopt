"""SVG optimization in pure Python (no external Node.js tools required)."""

from __future__ import annotations

import re

# Attribute values that match the SVG initial value and can be removed safely.
# Only non-inherited properties can be removed without context; inherited
# properties like fill or stroke would break documents where a parent element
# has set a different value.
_DEFAULT_ATTRS: dict[str, set[str]] = {
    "opacity": {"1", "1.0"},
}

# Attributes known to contain pure numeric/coordinate data. Other attributes
# (id, class, href, fill, etc.) may contain identifiers or URLs and must not
# have their text transformed.
_ROUNDABLE_ATTRS: set[str] = {
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "width",
    "height",
    "d",
    "points",
    "viewbox",
    "transform",
    "gradienttransform",
    "patterntransform",
    "stroke-width",
    "stroke-dashoffset",
    "stroke-miterlimit",
    "font-size",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    "stop-opacity",
    "offset",
}

# Match an XML element tag. This is deliberately conservative: it will not touch
# text content, CDATA sections, or invalid markup.
_TAG_RE = re.compile(r"<[^>]+>")

# Match a single attribute inside a tag. Handles double quotes, single quotes
# and unquoted values (the latter are re-quoted on output to guarantee valid XML).
_ATTR_RE = re.compile(r"\s+([a-zA-Z_:][\w:.-]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^>\s]+))")

# Match a CDATA section so it can be protected while tags are processed.
_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


def _round_decimals(value: str) -> str:
    """Round numeric values with 4+ decimal places to 3 places."""

    def _round_match(match: re.Match[str]) -> str:
        num = float(match.group(0))
        rounded = round(num, 3)
        result = f"{rounded:.3f}".rstrip("0").rstrip(".")
        return result if result != "-0" else "0"

    return re.sub(r"-?\d+\.\d{4,}", _round_match, value)


def _quote(value: str) -> str:
    """Return a properly quoted attribute value."""
    if '"' not in value:
        return f'"{value}"'
    if "'" not in value:
        return f"'{value}'"
    escaped = value.replace('"', "&quot;")
    return f'"{escaped}"'


def _minify_tag(match: re.Match[str]) -> str:
    """Process a single tag: remove defaults/empty attrs and round long decimals."""
    tag = match.group(0)

    # Leave closing tags untouched.
    if tag.startswith("</"):
        return tag

    name_match = re.match(r"<([a-zA-Z_:][\w:.-]*)", tag)
    if not name_match:
        return tag
    name = name_match.group(1)

    attrs: list[tuple[str, str]] = []
    for attr_match in _ATTR_RE.finditer(tag):
        attr_name = attr_match.group(1)
        attr_key = attr_name.lower()
        value = next(g for g in attr_match.group(2, 3, 4) if g is not None).strip()

        if attr_key in _DEFAULT_ATTRS and value.lower() in _DEFAULT_ATTRS[attr_key]:
            continue
        if value == "":
            continue

        if attr_key in _ROUNDABLE_ATTRS:
            rounded = _round_decimals(value)
            if rounded != value:
                value = rounded

        attrs.append((attr_name, _quote(value)))

    attr_str = "".join(f" {n}={v}" for n, v in attrs)
    if tag.rstrip().endswith("/>"):
        return f"<{name}{attr_str} />"
    return f"<{name}{attr_str}>"


def optimize_svg(data: str | bytes) -> str:
    """Minify an SVG by removing comments and default attributes.

    Args:
        data: Raw SVG content as str or bytes.

    Returns:
        Optimized SVG string.

    """
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    # Remove XML declaration.
    data = re.sub(r"<\?xml[^?]*\?>", "", data)

    # Remove DOCTYPE.
    data = re.sub(r"<!DOCTYPE[^>]*>", "", data, flags=re.IGNORECASE)

    # Remove HTML comments.
    data = re.sub(r"<!--.*?-->", "", data, flags=re.DOTALL)

    # Protect CDATA sections so the tag processor does not touch their content.
    cdata_blocks: list[str] = []

    def _store_cdata(cdata_match: re.Match[str]) -> str:
        placeholder = f"__CDATA_{len(cdata_blocks)}__"
        cdata_blocks.append(cdata_match.group(0))
        return placeholder

    data = _CDATA_RE.sub(_store_cdata, data)

    # Process individual tags.
    data = _TAG_RE.sub(_minify_tag, data)

    # Restore CDATA sections.
    for index, block in enumerate(cdata_blocks):
        data = data.replace(f"__CDATA_{index}__", block, 1)

    return data.strip()
