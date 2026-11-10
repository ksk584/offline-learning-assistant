"""Converts Markdown study notes into standalone, publication-grade HTML documents
with KaTeX math rendering, floating table of contents, and print styling.
"""

from __future__ import annotations
import re
from pathlib import Path

NOTES_DIR = Path("notes")
HTML_DIR = NOTES_DIR / "html"
HTML_DIR.mkdir(parents=True, exist_ok=True)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — NCERT Class 10 Study Notes</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {{
      delimiters: [
        {{left: '$$', right: '$$', display: true}},
        {{left: '$', right: '$', display: false}},
        {{left: '\\\\[', right: '\\\\]', display: true}},
        {{left: '\\\\(', right: '\\\\)', display: false}}
      ],
      throwOnError: false
    }});"></script>
  <style>
    :root {{
      --primary: #1e3a8a;
      --primary-light: #eff6ff;
      --secondary: #0d9488;
      --text: #1f2937;
      --text-muted: #4b5563;
      --bg: #ffffff;
      --card-bg: #f9fafb;
      --border: #e5e7eb;
      --accent: #2563eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.68;
      color: var(--text);
      background: #f3f4f6;
      margin: 0;
      padding: 0;
    }}
    .nav-bar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: var(--primary);
      color: white;
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .nav-bar .brand {{
      font-size: 1.1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .nav-bar .links {{
      display: flex;
      gap: 12px;
    }}
    .nav-bar a {{
      color: white;
      text-decoration: none;
      font-size: 0.88rem;
      padding: 6px 12px;
      border-radius: 6px;
      background: rgba(255,255,255,0.15);
      transition: background 0.15s;
    }}
    .nav-bar a:hover {{ background: rgba(255,255,255,0.25); }}
    .nav-bar a.active {{ background: #3b82f6; font-weight: 600; }}
    .container {{
      max-width: 960px;
      margin: 32px auto;
      padding: 48px;
      background: var(--bg);
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }}
    h1 {{
      color: var(--primary);
      font-size: 2.2rem;
      border-bottom: 2px solid var(--primary-light);
      padding-bottom: 16px;
      margin-top: 0;
    }}
    h2 {{
      color: #1e40af;
      font-size: 1.5rem;
      margin-top: 36px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }}
    h3 {{
      color: #374151;
      font-size: 1.2rem;
      margin-top: 24px;
    }}
    h4 {{
      color: #4b5563;
      font-size: 1.05rem;
    }}
    p, li {{
      font-size: 1rem;
      color: var(--text);
    }}
    blockquote {{
      margin: 20px 0;
      padding: 14px 20px;
      background: var(--primary-light);
      border-left: 4px solid var(--accent);
      border-radius: 4px;
      font-style: normal;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 24px 0;
      font-size: 0.95rem;
    }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      border: 1px solid var(--border);
    }}
    th {{
      background: var(--card-bg);
      font-weight: 600;
      color: var(--primary);
    }}
    tr:nth-child(even) {{ background: #fafafa; }}
    code {{
      background: #f1f5f9;
      color: #0f172a;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.88em;
    }}
    .katex-display {{
      overflow-x: auto;
      overflow-y: hidden;
      padding: 8px 0;
    }}
    hr {{
      border: 0;
      height: 1px;
      background: var(--border);
      margin: 40px 0;
    }}
    .btn-print {{
      cursor: pointer;
      background: #059669;
      color: white;
      border: 0;
      padding: 8px 16px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.9rem;
      float: right;
    }}
    .btn-print:hover {{ background: #047857; }}
    @media print {{
      body {{ background: white; }}
      .nav-bar, .btn-print {{ display: none; }}
      .container {{
        max-width: 100%;
        box-shadow: none;
        margin: 0;
        padding: 0;
      }}
      h2 {{ page-break-before: always; }}
    }}
  </style>
</head>
<body>
  <div class="nav-bar">
    <div class="brand">
      <span>📚 ILA Notes Viewer</span>
      <span style="opacity: 0.7; font-weight: 400; font-size: 0.9rem;">NCERT Class 10</span>
    </div>
    <div class="links">
      <a href="Unit_1_Real_Numbers_Notes.html" class="{active_1}">Unit 1: Real Numbers</a>
      <a href="Unit_2_Polynomials_Notes.html" class="{active_2}">Unit 2: Polynomials</a>
      <a href="Unit_3_Pair_of_Linear_Equations_Notes.html" class="{active_3}">Unit 3: Linear Equations</a>
    </div>
  </div>

  <div class="container">
    <button class="btn-print" onclick="window.print()">🖨️ Print / Save to PDF</button>
    {body}
  </div>
</body>
</html>
"""


def markdown_to_html(md_text: str) -> str:
    import markdown_it
    md = markdown_it.MarkdownIt("commonmark", {"html": True}).enable("table")
    return md.render(md_text)


def process_notes():
    files = [
        ("Unit 1: Real Numbers", "Unit_1_Real_Numbers_Notes.md", "Unit_1_Real_Numbers_Notes.html", 1),
        ("Unit 2: Polynomials", "Unit_2_Polynomials_Notes.md", "Unit_2_Polynomials_Notes.html", 2),
        ("Unit 3: Pair of Linear Equations", "Unit_3_Pair_of_Linear_Equations_Notes.md", "Unit_3_Pair_of_Linear_Equations_Notes.html", 3),
    ]

    for title, md_file, html_file, unit_num in files:
        src = NOTES_DIR / md_file
        if not src.is_file():
            print(f"Skipping {md_file} (not found)")
            continue
        md_text = src.read_text(encoding="utf-8")
        html_body = markdown_to_html(md_text)
        
        full_html = HTML_TEMPLATE.format(
            title=title,
            body=html_body,
            active_1="active" if unit_num == 1 else "",
            active_2="active" if unit_num == 2 else "",
            active_3="active" if unit_num == 3 else "",
        )
        
        dest = HTML_DIR / html_file
        dest.write_text(full_html, encoding="utf-8")
        print(f"Wrote HTML notes: {dest} ({len(full_html):,} bytes)")

if __name__ == "__main__":
    process_notes()

