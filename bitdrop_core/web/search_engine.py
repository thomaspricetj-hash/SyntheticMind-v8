import requests
import time
import json
import os
from typing import List, Dict


class WebSearchEngine:
    """
    Universal FREE DuckDuckGo search engine with:
        • Session cookie support (required in 2024–2026)
        • Modern browser headers
        • Multi‑variant HTML parsing (A–E)
        • Local in‑memory + disk cache
        • TTL expiration
        • Fail‑soft behavior
    """

    CACHE_TTL = 60 * 60 * 6          # 6 hours
    CACHE_FILE = "web_cache.json"

    def __init__(self, timeout: int = 8, enable_disk_cache: bool = True):
        self.timeout = timeout
        self.enable_disk_cache = enable_disk_cache
        self.cache: Dict[str, Dict] = {}

        if enable_disk_cache:
            self._load_cache()

        # Modern browser headers (required or DDG returns empty results)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://duckduckgo.com/",
        }

        # DDG session cookie (forces real results)
        self.cookies = {
            "kl": "us-en",   # force English results
        }

    # ------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        key = query.lower().strip()

        # 1. Cache lookup
        cached = self._cache_get(key)
        if cached:
            return cached

        # 2. Real search
        try:
            results = self._search_ddg(query, top_k)
        except Exception:
            results = []

        # 3. Cache store
        if results:
            self._cache_set(key, results)

        return results

    # ------------------------------------------------------------
    # INTERNAL: DDG HTML parser (multi‑variant)
    # ------------------------------------------------------------
    def _search_ddg(self, query: str, top_k: int) -> List[Dict]:
        url = "https://duckduckgo.com/html/"
        params = {"q": query}

        try:
            resp = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers=self.headers,
                cookies=self.cookies,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception:
            return []

        results: List[Dict[str, str]] = []

        # Variant A: <div class="result">
        blocks = html.split('<div class="result">')
        if len(blocks) > 1:
            for block in blocks[1:]:
                if len(results) >= top_k:
                    break
                parsed = self._parse_block(block)
                if parsed["title"] or parsed["snippet"]:
                    results.append(parsed)
            if results:
                return results

        # Variant B: <a class="result__a">
        blocks = html.split('<a class="result__a"')
        if len(blocks) > 1:
            for block in blocks[1:]:
                if len(results) >= top_k:
                    break
                parsed = self._parse_block(block)
                if parsed["title"] or parsed["snippet"]:
                    results.append(parsed)
            if results:
                return results

        # Variant C: <div class="nrn-react-div">
        blocks = html.split('<div class="nrn-react-div"')
        if len(blocks) > 1:
            for block in blocks[1:]:
                if len(results) >= top_k:
                    break
                parsed = self._parse_block(block)
                if parsed["title"] or parsed["snippet"]:
                    results.append(parsed)
            if results:
                return results

        # Variant D: <div class="result__body">
        blocks = html.split('<div class="result__body">')
        if len(blocks) > 1:
            for block in blocks[1:]:
                if len(results) >= top_k:
                    break
                parsed = self._parse_block(block)
                if parsed["title"] or parsed["snippet"]:
                    results.append(parsed)
            if results:
                return results

        # Variant E: <article class="nrn-react-div">
        blocks = html.split('<article class="nrn-react-div"')
        if len(blocks) > 1:
            for block in blocks[1:]:
                if len(results) >= top_k:
                    break
                parsed = self._parse_block(block)
                if parsed["title"] or parsed["snippet"]:
                    results.append(parsed)
            if results:
                return results

        return results

    # ------------------------------------------------------------
    # BLOCK PARSER
    # ------------------------------------------------------------
    def _parse_block(self, block: str) -> Dict[str, str]:
        # Title: try multiple patterns
        title = ""
        title_patterns = [
            ('<a class="result__a"', '</a>'),
            ('<h2', '</h2>'),
            ('<h3', '</h3>'),
        ]
        for start, end in title_patterns:
            title = self._extract_between(block, start, end)
            if title:
                break
        title = self._strip_html(title)

        # URL
        url = self._extract_href(block)

        # Snippet: try multiple patterns
        snippet = ""
        snippet_patterns = [
            ('<a class="result__snippet"', '</a>'),
            ('<div class="result__snippet"', '</div>'),
            ('<span class="result__snippet"', '</span>'),
        ]
        for start, end in snippet_patterns:
            snippet = self._extract_between(block, start, end)
            if snippet:
                break
        snippet = self._strip_html(snippet)

        return {
            "title": title,
            "snippet": snippet,
            "url": url,
        }

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------
    def _extract_between(self, text: str, start_marker: str, end_marker: str) -> str:
        if start_marker not in text:
            return ""
        part = text.split(start_marker, 1)[1]
        if ">" in part:
            part = part.split(">", 1)[1]
        if end_marker in part:
            part = part.split(end_marker, 1)[0]
        return part.strip()

    def _extract_href(self, block: str) -> str:
        if 'href="' not in block:
            return ""
        part = block.split('href="', 1)[1]
        return part.split('"', 1)[0].strip()

    def _strip_html(self, text: str) -> str:
        import re
        text = re.sub(r"<.*?>", "", text)
        return (
            text.replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
            .strip()
        )

    # ------------------------------------------------------------
    # CACHE
    # ------------------------------------------------------------
    def _cache_get(self, key: str):
        entry = self.cache.get(key)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > self.CACHE_TTL:
            return None
        return entry["results"]

    def _cache_set(self, key: str, results: List[Dict]):
        self.cache[key] = {
            "timestamp": time.time(),
            "results": results,
        }
        if self.enable_disk_cache:
            self._save_cache()

    def _load_cache(self):
        if not os.path.exists(self.CACHE_FILE):
            return
        try:
            with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                self.cache = json.load(f)
        except Exception:
            self.cache = {}

    def _save_cache(self):
        try:
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f)
        except Exception:
            pass



