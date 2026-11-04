"""Build Docapella and adapt its output to a GitHub Pages project path."""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import html
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site/_build"
PREFIX = "/electoral-systems"
ORIGIN = "https://bnm2f28k6s.github.io"


def site_url(value):
    value = html.unescape(value)
    if value.startswith(ORIGIN + "/"):
        return ORIGIN + site_url(value[len(ORIGIN):])
    if not value.startswith("/") or value.startswith("//"):
        return value
    parts = urlsplit(value)
    path = parts.path
    if path == PREFIX or path.startswith(PREFIX + "/"):
        return value
    target = OUT / path.lstrip("/")
    if target.is_dir() and (target / "index.html").exists():
        path = path.rstrip("/") + "/"
    elif not target.is_file() and target.with_suffix(".html").is_file():
        path += ".html"
    return urlunsplit(("", "", PREFIX + path, parts.query, parts.fragment))


def main():
    subprocess.run([str(ROOT / "bin/docapella"), "build"], cwd=ROOT / "site", check=True)
    for page in OUT.rglob("*.html"):
        text = page.read_text()
        text = re.sub(r'(?<![:\w-])(href|src)="([^"]*)"',
                      lambda m: m[1] + '="' + html.escape(site_url(m[2]), quote=True) + '"', text)
        text = text.replace("/_assets/search.json", PREFIX + "/_assets/search.json")
        page.write_text(text)
    index = OUT / "_assets/search.json"
    data = json.loads(index.read_text())
    for doc in data["documentStore"]["docs"].values():
        doc["page_url"] = site_url(doc["page_url"])
    index.write_text(json.dumps(data, ensure_ascii=False))
    (OUT / ".nojekyll").touch()
    print("Prepared GitHub Pages output at", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
