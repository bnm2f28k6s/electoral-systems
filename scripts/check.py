"""Check generated local URLs, fragments, search coverage and output privacy."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site/_build"
PREFIX = "/electoral-systems/"


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        # Skip Alpine's dynamic :href and x-bind:href expressions.
        for name in ("href", "src"):
            if name in attrs and attrs[name] != "item.page_url":
                self.links.append(attrs[name])


def main():
    pages = {p: Page(p.read_text()) for p in OUT.rglob("*.html")}
    assert len(pages) == 5, "Unexpected published page count"
    checked = 0

    def check_link(url, source):
        nonlocal checked
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            return
        if not parts.path:
            target = source
        else:
            assert parts.path.startswith(PREFIX), f"Unprefixed URL: {url}"
            target = OUT / unquote(parts.path[len(PREFIX):])
            if target.is_dir():
                target /= "index.html"
            assert target.is_file(), f"Missing target: {url}"
        if parts.fragment and target in pages:
            assert unquote(parts.fragment) in pages[target].ids, f"Missing fragment: {url}"
        checked += 1

    for path, page in pages.items():
        for url in page.links:
            check_link(url, path)
    data = json.loads((OUT / "_assets/search.json").read_text())
    docs = data["documentStore"]["docs"].values()
    for doc in docs:
        check_link(doc["page_url"], OUT / "index.html")
    assert any("algorithm" in d.get("title", "").lower() for d in docs)
    for path in OUT.rglob("*"):
        if path.is_file():
            assert not re.search(rb"/Users/|/home/runner/|BEGIN .*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{20,}", path.read_bytes()), "Potential private data in output"
    for args in (["git", "diff", "--check"], ["git", "diff", "--cached", "--check"]):
        subprocess.run(args, cwd=ROOT, check=True)
    print(f"PASS: {len(pages)} HTML pages; {checked} local links/search targets; fragments, search coverage, output privacy and Git whitespace")


if __name__ == "__main__":
    main()
