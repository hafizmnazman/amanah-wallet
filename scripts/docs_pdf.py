"""The technical documentation and the security self-assessment as PDFs (decision E-37): Markdown to print-ready HTML.

    uv run --with markdown==3.7 python scripts/docs_pdf.py . /tmp/amanah-pdf
    NODE_PATH=frontend/node_modules node scripts/docs_pdf.js /tmp/amanah-pdf docs

Mermaid, KaTeX and the fonts load from public CDNs when Chromium opens the page, and relative links become
links to the repository on GitHub, so they still work from a PDF. docs_pdf.js prints each page once all three
are ready.
"""
import html
import re
import sys
import unicodedata
from pathlib import Path

import markdown

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
GITHUB = "https://github.com/hafizmnazman/amanah-wallet"

DOCS = {
    "technical-documentation": {"title": "Technical documentation", "kicker": "Amanah"},
    "security-self-assessment": {"title": "Security self-assessment", "kicker": "Amanah"},
    "security-self-assessment-short": {"title": "Security self-assessment, short report", "kicker": "Amanah"},
}


def slugify(value, separator="-"):
    """GitHub's heading anchors: lowercase, punctuation dropped, spaces to hyphens."""
    value = unicodedata.normalize("NFKC", html.unescape(re.sub(r"<[^>]+>", "", value))).lower()
    value = re.sub(r"[^\w\- ]", "", value)
    return value.replace(" ", separator)


def protect(text):
    """Mermaid fences and display math leave the Markdown pass untouched."""
    kept = []

    def keep(kind, body):
        kept.append((kind, body))
        return f"\n\nKEPTBLOCK{len(kept) - 1}KEPTBLOCK\n\n"

    text = re.sub(r"```mermaid\n(.*?)```", lambda m: keep("mermaid", m.group(1)), text, flags=re.S)
    text = re.sub(r"\$\$(.+?)\$\$", lambda m: keep("math", m.group(1)), text, flags=re.S)
    return text, kept


def restore(body, kept):
    for i, (kind, content) in enumerate(kept):
        if kind == "mermaid":
            caption = ("Figure 1. Data flow. It is vector, so it stays sharp when zoomed; the README on GitHub draws "
                       "the same diagram at full size.")
            block = (f'<figure class="diagram"><pre class="mermaid">{html.escape(content)}</pre>'
                     f'<figcaption>{caption}</figcaption></figure>')
        else:
            block = f'<div class="math">$${html.escape(content)}$$</div>'
        body = body.replace(f"<p>KEPTBLOCK{i}KEPTBLOCK</p>", block).replace(f"KEPTBLOCK{i}KEPTBLOCK", block)
    return body


def absolute_links(body, doc_dir):
    """Relative links point into the repository on GitHub, so they work from a PDF."""

    def fix(match):
        href = html.unescape(match.group(1))
        if re.match(r"^(https?:|mailto:|#)", href):
            return match.group(0)
        path, _, anchor = href.partition("#")
        target = (doc_dir / path).resolve() if path else None
        rel = target.relative_to(REPO.resolve()).as_posix() if target else ""
        kind = "tree" if (path.endswith("/") or (target and target.is_dir())) else "blob"
        url = f"{GITHUB}/{kind}/main/{rel}" + (f"#{anchor}" if anchor else "")
        return f'href="{html.escape(url)}"'

    return re.sub(r'href="([^"]+)"', fix, body)


CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
:root { --ink: #1b2333; --muted: #5b6577; --navy: #0B1F4B; --blue: #1D4ED8; --gold: #D8A521; --rule: #d9dee8; --tint: #f4f7fc; }
html { font-size: 10pt; }
body { font-family: "Source Serif 4", Georgia, serif; color: var(--ink); line-height: 1.45; margin: 0; background: #fff; }
h1, h2, h3, h4, .kicker, th { font-family: "Inter", "Helvetica Neue", Arial, sans-serif; }
h1 { font-size: 22pt; line-height: 1.15; color: var(--navy); margin: 0 0 6pt; letter-spacing: -0.01em; }
h2 { font-size: 13.5pt; color: var(--navy); margin: 18pt 0 6pt; padding-bottom: 3pt; border-bottom: 1.5pt solid var(--gold); break-after: avoid; }
h3 { font-size: 11pt; color: var(--navy); margin: 13pt 0 4pt; break-after: avoid; }
h4 { font-size: 10pt; margin: 10pt 0 3pt; break-after: avoid; }
p { margin: 0 0 6pt; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 6pt 16pt; padding: 0; }
li { margin: 0 0 2.5pt; }
a { color: var(--blue); text-decoration: none; }
code { font-family: "JetBrains Mono", Consolas, monospace; font-size: 8.2pt; background: var(--tint); padding: 0.5pt 2.5pt; border-radius: 2pt; overflow-wrap: break-word; }
td code { font-size: 7.6pt; }
pre { font-family: "JetBrains Mono", Consolas, monospace; font-size: 7.8pt; line-height: 1.4; background: var(--tint); border: 0.6pt solid var(--rule); border-radius: 3pt; padding: 6pt 8pt; white-space: pre-wrap; overflow-wrap: anywhere; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
pre.mermaid { background: #fff; border: 0.6pt solid var(--rule); text-align: center; white-space: pre; }
figure.diagram { margin: 6pt 0 10pt; break-inside: avoid; }
figure.diagram pre.mermaid { padding: 4pt; margin: 0; }
figure.diagram pre.mermaid svg { width: 100% !important; max-width: 100% !important; height: auto; }
figcaption { font-family: "Inter", Arial, sans-serif; font-size: 7.8pt; color: var(--muted); margin-top: 3pt; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 9pt; font-size: 8.3pt; line-height: 1.35; }
th { text-align: left; font-size: 7.8pt; text-transform: lowercase; color: var(--navy); background: var(--tint); border-bottom: 1pt solid var(--navy); padding: 3pt 4pt; }
td { vertical-align: top; border-bottom: 0.5pt solid var(--rule); padding: 3pt 4pt; }
tr { break-inside: avoid; }
blockquote { margin: 6pt 0; padding: 6pt 10pt; border-left: 2.5pt solid var(--gold); background: #fbf7ea; }
blockquote p:last-child { margin: 0; }
sub { font-size: 8pt; color: var(--muted); }
.math { text-align: center; margin: 8pt 0; font-size: 10.5pt; }
.titleblock { padding: 0 0 10pt; margin: 0 0 14pt; border-bottom: 0.8pt solid var(--rule); }
.kicker { color: var(--gold); font-weight: 700; font-size: 9pt; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 8pt; }
.titleblock p { color: var(--muted); margin: 2pt 0; }
.lead { font-size: 10.5pt; }
"""

FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600"
         "&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap")

SCRIPT = """
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
window.addEventListener("load", async () => {
  try {
    await document.fonts.ready;
    if (document.querySelector("pre.mermaid")) {
      mermaid.initialize({ startOnLoad: false, theme: "neutral", flowchart: { htmlLabels: false, curve: "basis", nodeSpacing: 22, rankSpacing: 34, padding: 6 },
                           themeVariables: { fontFamily: "Inter, Arial, sans-serif", fontSize: "17px" } });
      await mermaid.run({ querySelector: "pre.mermaid" });
    }
    document.querySelectorAll(".math").forEach((el) => renderMathInElement(el, { delimiters: [{ left: "$$", right: "$$", display: true }] }));
    await document.fonts.ready;
  } catch (e) { document.body.setAttribute("data-error", String(e)); }
  window.__ready = true;
});
</script>
"""


def build(name, meta):
    src = REPO / "docs" / f"{name}.md"
    text, kept = protect(src.read_text(encoding="utf-8"))
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"],
                           extension_configs={"toc": {"slugify": slugify}})
    body = restore(md.convert(text), kept)
    body = absolute_links(body, src.parent)
    # Long identifiers break after underscores, slashes and dots, never mid-word
    body = re.sub(r"<code>(.*?)</code>", lambda c: "<code>" + re.sub(r"([_/.])", "\\g<1><wbr>", c.group(1)) + "</code>", body)
    # The opening heading and the lines under it become the title block
    m = re.match(r"\s*<h1[^>]*>(.*?)</h1>\s*((?:<p>.*?</p>\s*){0,3})", body, flags=re.S)
    if m:
        title, lines = m.group(1), m.group(2)
        rest = body[m.end():]
        if name.startswith("security-self-assessment"):
            title = "Amanah: Security Self-Assessment" + (", Short Report" if name.endswith("short") else "")
            rest = lines + rest
            lines = ("<p>20 October 2026. Abdul Hafiz Bin Mohd Noor Azman and Muhammad Khaidhir Bin Mohd Razin, "
                     "Universiti Teknologi PETRONAS; advisor Assoc. Prof. Ts. Dr. Khaironi Yatim Sharif</p>")
        block = f'<div class="titleblock"><div class="kicker">{meta["kicker"]} &middot; {meta["title"]}</div><h1>{title}</h1>{lines}</div>'
        body = block + rest
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Amanah: {meta["title"]}</title>'
            f'<link rel="stylesheet" href="{FONTS}"><style>{CSS}</style></head><body>{body}{SCRIPT}</body></html>')
    out = OUT / f"{name}.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}")


for name, meta in DOCS.items():
    build(name, meta)
