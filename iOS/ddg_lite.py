"""
ddg_lite - DuckDuckGo backend without lxml, for DorkEye on iSH / Alpine.

Drop-in replacement for `ddgs.DDGS().text()`: same call signature and the
same result keys ("title", "href", "body"). Uses only requests + bs4 with
the stdlib "html.parser", so nothing needs to be compiled.

iOS/install_ish.sh copies this file into the DorkEye root, where
dorkeye.py picks it up automatically when `ddgs` is not installed.

Python 3.8+
"""
import time
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

URL = "https://html.duckduckgo.com/html/"
UA = "Mozilla/5.0 (X11; Linux x86_64)"
PAGE_DELAY = 1.5  # seconds between result pages


class RatelimitException(Exception):
    """Raised when DuckDuckGo answers with its rate-limit page (HTTP 202)."""


class DDGS:
    def __init__(self, headers=None, proxy=None, timeout=20, **kw):
        self.session = requests.Session()
        self.session.headers.update(headers or {"User-Agent": UA})
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.session.close()
        return False

    def _post(self, data):
        r = self.session.post(URL, data=data, timeout=self.timeout)
        if r.status_code == 202:
            raise RatelimitException("DuckDuckGo rate limit (HTTP 202)")
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")

    @staticmethod
    def _parse(soup):
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if "uddg=" in href:
                href = unquote(parse_qs(urlparse(href).query).get("uddg", [""])[0])
            if href.startswith("//"):
                href = "https:" + href
            box = a.find_parent(class_="result")
            snip = box.select_one(".result__snippet") if box else None
            yield {
                "title": a.get_text(strip=True),
                "href": href,
                "body": snip.get_text(strip=True) if snip else "",
            }

    @staticmethod
    def _next_page(soup):
        """Hidden inputs of the "Next" form, or None on the last page."""
        for form in soup.select(".nav-link form"):
            btn = form.find("input", attrs={"type": "submit"})
            if btn and "next" in (btn.get("value", "").lower()):
                return {
                    i.get("name"): i.get("value", "")
                    for i in form.find_all("input")
                    if i.get("name")
                }
        return None

    def text(self, keywords, region="wt-wt", safesearch="moderate",
             timelimit=None, max_results=10, **kw):
        data = {"q": keywords, "kl": region}
        if timelimit:  # d, w, m, y
            data["df"] = timelimit
        if safesearch == "off":
            data["kp"] = "-2"
        elif safesearch == "on":
            data["kp"] = "1"

        out, seen = [], set()
        while True:
            try:
                soup = self._post(data)
            except (RatelimitException, requests.RequestException):
                # First page failing is a real error; on later pages keep
                # the results already collected instead of losing them.
                if not out:
                    raise
                return out
            for item in self._parse(soup):
                if not item["href"] or item["href"] in seen:
                    continue
                seen.add(item["href"])
                out.append(item)
                if max_results and len(out) >= max_results:
                    return out
            data = self._next_page(soup)
            if not data:
                return out
            time.sleep(PAGE_DELAY)
