#!/usr/bin/env python3
"""build_viewer.py — generate a self-contained, read-only HTML viewer for the live_docs KB.

Export contract (the stable spine): each doc becomes a JSON object that is LITERALLY its
frontmatter plus one added field `body` (raw, unrendered markdown). The whole KB is a JS
array of these objects, inlined into a single HTML file. Reviews are exported the same way.

No server-side rendering, no precomputed HTML, no graph precomputation. Markdown and the
wiki-link resolver run entirely client-side. The output opens from file:// with no network.

Usage:
    python3 scripts/build_viewer.py            # reads paths from livedocs.config.json
    python3 scripts/build_viewer.py --out build/viewer.html

We read the doc files directly (frontmatter + body) rather than going through the ldoc
porcelain: this is a one-shot static export, the frontmatter IS the contract, and reading
files keeps the export trivially faithful to on-disk state. (Per project principle the
porcelain is preferred for live queries; a bulk static dump is the documented exception.)
"""
import argparse
import json
import os
import sys
import re

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def load_config():
    cfg_path = os.path.join(REPO, "livedocs.config.json")
    with open(cfg_path) as f:
        return json.load(f)


def split_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return fm, m.group(2)


def load_dir(path):
    out = []
    if not os.path.isdir(path):
        return out
    for name in sorted(os.listdir(path)):
        if not name.endswith(".md"):
            continue
        full = os.path.join(path, name)
        with open(full, encoding="utf-8") as f:
            text = f.read()
        fm, body = split_frontmatter(text)
        # id should match filename stem; trust frontmatter id, fall back to stem
        if "id" not in fm:
            fm["id"] = os.path.splitext(name)[0]
        fm["id"] = str(fm["id"])
        rec = dict(fm)            # the export contract: frontmatter ...
        rec["body"] = body.strip()  # ... plus the raw body
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "build", "viewer.html"))
    args = ap.parse_args()

    cfg = load_config()
    docs_dir = os.path.join(REPO, cfg["docs"])
    reviews_dir = os.path.join(REPO, cfg["reviews"])

    docs = load_dir(docs_dir)
    reviews = load_dir(reviews_dir)

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer_template.html")
    with open(tpl_path, encoding="utf-8") as f:
        template = f.read()

    docs_json = json.dumps(docs, ensure_ascii=False)
    reviews_json = json.dumps(reviews, ensure_ascii=False)

    # Inline the vendored markdown renderer so the file works offline from file://.
    marked_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor_marked.min.js")
    with open(marked_path, encoding="utf-8") as f:
        marked_js = f.read()

    html = template.replace("/*__DOCS_JSON__*/", docs_json)
    html = html.replace("/*__REVIEWS_JSON__*/", reviews_json)
    html = html.replace("/*__MARKED_JS__*/", marked_js)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {out_path}")
    print(f"  docs:    {len(docs)}")
    print(f"  reviews: {len(reviews)}")


if __name__ == "__main__":
    main()
