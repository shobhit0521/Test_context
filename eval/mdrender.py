"""Render a Markdown file into a clean, self-contained HTML document.

Reusable for METRICS.md now and the results report later. Usage:
    python3 mdrender.py METRICS.md            # -> METRICS.html
    python3 mdrender.py METRICS.md out.html
"""

from __future__ import annotations

import sys
from pathlib import Path

import markdown

CSS = """
:root{--fg:#1a1a2e;--muted:#6b7280;--accent:#2ca02c;--card:#f7f8fa;--border:#e5e7eb;}
*{box-sizing:border-box}
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--fg);
max-width:900px;margin:0 auto;padding:44px 26px;line-height:1.6}
h1{font-size:30px;margin-bottom:2px}
h2{margin-top:36px;border-bottom:2px solid var(--border);padding-bottom:6px}
h3{margin-top:24px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}
th,td{border:1px solid var(--border);padding:8px 11px;text-align:left;vertical-align:top}
th{background:#f0f2f5}
code{background:#f0f2f5;padding:2px 6px;border-radius:4px;font-size:13px}
pre{background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:8px;overflow:auto}
pre code{background:none;color:inherit;padding:0}
blockquote{border-left:4px solid var(--accent);margin:0;padding:6px 16px;background:var(--card);
border-radius:0 8px 8px 0}
a{color:#2563eb}
"""


def render(md_path: Path, out_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "toc", "sane_lists"]
    )
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{md_path.stem}</title><style>{CSS}</style></head><body>"
        f"{body}</body></html>"
    )
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python3 mdrender.py <file.md> [out.html]")
    md_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else md_path.with_suffix(".html")
    print("wrote", render(md_path, out_path))


if __name__ == "__main__":
    main()
