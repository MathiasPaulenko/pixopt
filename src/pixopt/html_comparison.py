"""Generate an interactive HTML before/after comparison slider."""

from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0d1117;
    color: #c9d1d9;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
    padding: 2rem;
  }}
  h1 {{ margin-bottom: 0.5rem; font-size: 1.5rem; }}
  .meta {{ color: #8b949e; margin-bottom: 1.5rem; font-size: 0.9rem; }}
  .container {{
    position: relative;
    width: {width}px;
    max-width: 100%;
    overflow: hidden;
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }}
  .img {{
    display: block;
    width: 100%;
    height: auto;
    user-select: none;
  }}
  .overlay {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    overflow: hidden;
  }}
  .overlay .img {{
    position: absolute;
    top: 0; left: 0;
    height: 100%;
    width: auto;
    max-width: none;
  }}
  .slider {{
    position: absolute;
    top: 0; bottom: 0;
    width: 4px;
    background: #fff;
    cursor: ew-resize;
    z-index: 10;
    box-shadow: 0 0 8px rgba(0,0,0,0.5);
  }}
  .slider::after {{
    content: "";
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 32px; height: 32px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  }}
  .label {{
    position: absolute;
    top: 12px;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: rgba(0,0,0,0.6);
    color: #fff;
    pointer-events: none;
  }}
  .label-before {{ left: 12px; }}
  .label-after {{ right: 12px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">{meta}</div>
<div class="container" id="container">
  <img class="img" src="{after_b64}" alt="after">
  <div class="overlay" id="overlay">
    <img class="img" src="{before_b64}" alt="before">
  </div>
  <div class="slider" id="slider" style="left: 50%;"></div>
  <div class="label label-before">Before</div>
  <div class="label label-after">After</div>
</div>

<script>
(function() {{
  const container = document.getElementById('container');
  const overlay = document.getElementById('overlay');
  const slider = document.getElementById('slider');
  let dragging = false;

  function update(x) {{
    const rect = container.getBoundingClientRect();
    let pct = ((x - rect.left) / rect.width) * 100;
    pct = Math.max(0, Math.min(100, pct));
    overlay.style.width = pct + '%';
    slider.style.left = pct + '%';
  }}

  slider.addEventListener('mousedown', () => dragging = true);
  window.addEventListener('mouseup', () => dragging = false);
  window.addEventListener('mousemove', e => {{ if (dragging) update(e.clientX); }});

  slider.addEventListener('touchstart', () => dragging = true, {{passive: true}});
  window.addEventListener('touchend', () => dragging = false);
  window.addEventListener('touchmove', e => {{ if (dragging) update(e.touches[0].clientX); }}, {{passive: true}});  # noqa: E501
}})();
</script>
</body>
</html>
"""


def _img_to_base64(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    if ext == "svg":
        mime = "image/svg+xml"
        data = path.read_bytes()
    else:
        mime = f"image/{ext.replace('jpg', 'jpeg')}"
        with Image.open(path) as img:
            img.load()
        data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def generate_comparison_html(
    before_path: Path,
    after_path: Path,
    output_html: Path,
    title: str = "Image Comparison",
) -> Path:
    """Generate a self-contained HTML file with an interactive before/after slider.

    Args:
        before_path: Path to the original image.
        after_path: Path to the optimized image.
        output_html: Path where the HTML file will be saved.
        title: Page title displayed above the slider.

    Returns:
        Path to the generated HTML file.
    """
    before_b64 = _img_to_base64(before_path)
    after_b64 = _img_to_base64(after_path)

    with Image.open(before_path) as img:
        width = img.width

    orig_size = before_path.stat().st_size
    opt_size = after_path.stat().st_size
    savings = orig_size - opt_size
    pct = savings / orig_size * 100 if orig_size > 0 else 0

    def _human(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.2f} MB"

    meta = (
        f"Original: {_human(orig_size)}  |  "
        f"Optimized: {_human(opt_size)}  |  "
        f"Savings: {_human(savings)} ({pct:.1f}%)"
    )

    html = HTML_TEMPLATE.format(
        title=title,
        meta=meta,
        before_b64=before_b64,
        after_b64=after_b64,
        width=width,
    )

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")
    return output_html
