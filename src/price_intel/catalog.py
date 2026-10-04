"""Bounded catalog ingestion with a durable run ledger and offline replay.

Only explicitly allowed HTTPS origins are fetched. This is a collector library,
not an arbitrary-URL HTTP API. The built-in source is a public scraping sandbox.
"""

import csv
import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

SOURCE = "https://books.toscrape.com"
USER_AGENT = "PriceIntelPortfolio/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_url(base: str, value: str, allowed_origin: str) -> str:
    url = urldefrag(urljoin(base, value))[0]
    parts = urlsplit(url)
    allowed = urlsplit(allowed_origin)
    if (
        parts.scheme != "https"
        or parts.netloc != allowed.netloc
        or parts.username
        or parts.password
    ):
        raise ValueError("URL outside configured HTTPS origin")
    return url


def product_row(name: str, price: str, currency: str, url: str) -> dict:
    name = " ".join(name.split())
    currency = currency.strip().upper()
    try:
        amount = Decimal(str(price).strip())
    except InvalidOperation as exc:
        raise ValueError("Invalid product price") from exc
    if not name or not amount.is_finite() or amount < 0 or len(currency) != 3 or not currency.isalpha():
        raise ValueError("Invalid product fields")
    return {
        "source": urlsplit(url).hostname,
        "product_id": hashlib.sha256(url.encode()).hexdigest()[:24],
        "product_name": name,
        "price": float(amount),
        "currency": currency,
        "source_url": url,
    }


def parse_catalog(html: str, page_url: str, origin: str = SOURCE) -> tuple[list[dict], str | None, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: dict[str, dict] = {}
    errors: list[str] = []

    # JSON-LD is common on real stores. Flatten graph/list containers without
    # assuming every script contains a valid Product or every offer is priced.
    def visit(node):
        if isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            if "@graph" in node:
                visit(node["@graph"])
            kind = node.get("@type", [])
            kind = [kind] if isinstance(kind, str) else kind
            if not isinstance(kind, list):
                return
            if "Product" in kind:
                offers = node.get("offers", {})
                offers = offers if isinstance(offers, list) else [offers]
                for offer in offers:
                    try:
                        product_url = node.get("url") or offer.get("url")
                        if not product_url:
                            raise ValueError("Product needs a stable source URL")
                        url = canonical_url(page_url, product_url, origin)
                        row = product_row(node["name"], offer["price"], offer["priceCurrency"], url)
                        rows[row["product_id"]] = row
                        break
                    except (KeyError, TypeError, AttributeError, ValueError):
                        errors.append("Invalid JSON-LD product/offer")

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            visit(json.loads(script.get_text()))
        except (ValueError, TypeError):
            errors.append("Malformed JSON-LD script")

    for card in soup.select("article.product_pod"):
        try:
            link = card.select_one("h3 a")
            price = card.select_one(".price_color").get_text(strip=True)
            url = canonical_url(page_url, link["href"], origin)
            row = product_row(link.get("title") or link.get_text(), price.removeprefix("£"), "GBP", url)
            rows[row["product_id"]] = row
        except (KeyError, TypeError, AttributeError, ValueError):
            errors.append("Invalid HTML product card")

    next_link = soup.select_one("li.next a, a[rel~=next]")
    next_url = None
    if next_link:
        try:
            next_url = canonical_url(page_url, next_link["href"], origin)
        except (KeyError, ValueError):
            errors.append("Rejected next-page URL")
    return list(rows.values()), next_url, errors


class CatalogStore:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, started_at TEXT NOT NULL, status TEXT NOT NULL,
              cursor TEXT, pages INTEGER NOT NULL DEFAULT 0, errors TEXT NOT NULL DEFAULT '[]');
            CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, body TEXT NOT NULL, fetched_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshots (
              run_id TEXT NOT NULL, product_id TEXT NOT NULL, page_url TEXT NOT NULL,
              captured_at TEXT NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(run_id, product_id), FOREIGN KEY(run_id) REFERENCES runs(id));
            CREATE TABLE IF NOT EXISTS visited_pages (
              run_id TEXT NOT NULL, url TEXT NOT NULL,
              PRIMARY KEY(run_id,url), FOREIGN KEY(run_id) REFERENCES runs(id));
            INSERT OR IGNORE INTO visited_pages SELECT DISTINCT run_id,page_url FROM snapshots;
        """)
        self.db.execute("PRAGMA foreign_keys=ON")

    def close(self):
        self.db.close()

    def rows(self, run_id: str | None = None) -> list[dict]:
        if run_id:
            records = self.db.execute("SELECT payload,captured_at FROM snapshots WHERE run_id=? ORDER BY product_id", (run_id,))
        else:
            records = self.db.execute("SELECT payload,captured_at FROM snapshots ORDER BY captured_at,product_id")
        return [{**json.loads(r["payload"]), "captured_at": r["captured_at"]} for r in records]

    def runs(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM runs ORDER BY started_at DESC")]


class CatalogCrawler:
    def __init__(self, store: CatalogStore, origin: str = SOURCE, *, client=None,
                 delay: float = 0.5, cache_ttl: float = 3600, sleep=time.sleep, renderer=None):
        self.store, self.origin = store, origin.rstrip("/")
        self.client = client or httpx.Client(timeout=20, follow_redirects=False, headers={"User-Agent": USER_AGENT})
        self.owns_client = client is None
        self.delay, self.cache_ttl, self.sleep = delay, cache_ttl, sleep
        self.renderer = renderer
        self.network_requests = 0
        self.cache_hits = 0

    def close(self):
        if self.owns_client:
            self.client.close()

    def fetch(self, url: str) -> str:
        canonical_url(self.origin, url, self.origin)
        cached = self.store.db.execute("SELECT body,fetched_at FROM cache WHERE url=?", (url,)).fetchone()
        if cached and time.time() - cached["fetched_at"] < self.cache_ttl:
            self.cache_hits += 1
            return cached["body"]
        for attempt in range(3):
            self.sleep(self.delay)
            try:
                self.network_requests += 1
                with self.client.stream("GET", url) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt == 2:
                            response.raise_for_status()
                        self.sleep(0.5 * 2**attempt)
                        continue
                    response.raise_for_status()
                    if 300 <= response.status_code < 400:
                        raise ValueError("Redirect rejected; configure the final origin explicitly")
                    content = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if len(content) + len(chunk) > 2_000_000:
                            raise ValueError("Page exceeds 2 MB limit")
                        content.extend(chunk)
                    # Bound decoded response bytes, including compressed responses.
                    body = content.decode("utf-8", errors="replace")
                with self.store.db:
                    self.store.db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (url, body, time.time()))
                return body
            except httpx.TransportError:
                if attempt == 2:
                    raise
                self.sleep(0.5 * 2**attempt)
        raise RuntimeError("Retry budget exhausted")

    def robot_policy(self) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            parser.parse(self.fetch(self.origin + "/robots.txt").splitlines())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                parser.parse([])
            else:
                raise
        return parser

    def crawl(self, start_url: str = SOURCE + "/", max_pages: int = 3, run_id: str | None = None) -> dict:
        if not 1 <= max_pages <= 50:
            raise ValueError("max_pages must be between 1 and 50")
        start_url = canonical_url(self.origin, start_url, self.origin)
        if run_id:
            state = self.store.db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not state:
                raise ValueError("Unknown run ID")
            if state["status"] == "completed":
                return {"run_id": run_id, "status": "completed", "rows": len(self.store.rows(run_id)), "pages": state["pages"]}
            cursor, pages, errors = state["cursor"], state["pages"], json.loads(state["errors"])
        else:
            run_id = str(uuid4())
            cursor, pages, errors = start_url, 0, []
            with self.store.db:
                self.store.db.execute("INSERT INTO runs(id,started_at,status,cursor) VALUES (?,?,?,?)", (run_id, utc_now(), "running", cursor))
        visited = {r[0] for r in self.store.db.execute("SELECT url FROM visited_pages WHERE run_id=?", (run_id,))}
        try:
            policy = self.robot_policy()
            for _ in range(max_pages):
                if not cursor:
                    break
                canonical_url(self.origin, cursor, self.origin)
                if cursor in visited:
                    raise ValueError("Pagination loop detected")
                if not policy.can_fetch(USER_AGENT, cursor):
                    raise ValueError("robots.txt disallows this page")
                rows, next_url, parse_errors = parse_catalog(self.fetch(cursor), cursor, self.origin)
                if not rows and self.renderer:
                    rows, next_url, parse_errors = parse_catalog(self.renderer(cursor), cursor, self.origin)
                if not rows:
                    raise ValueError("No valid products: parser/source mismatch")
                if "Rejected next-page URL" in parse_errors:
                    raise ValueError("Rejected next-page URL; pagination is incomplete")
                errors.extend({"url": cursor, "message": e} for e in parse_errors)
                captured_at = utc_now()
                # Page records and continuation cursor commit together. A retry
                # after interruption never duplicates this run's product rows.
                with self.store.db:
                    self.store.db.execute("INSERT INTO visited_pages VALUES (?,?)", (run_id, cursor))
                    for row in rows:
                        self.store.db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)", (run_id, row["product_id"], cursor, captured_at, json.dumps(row)))
                    pages += 1
                    self.store.db.execute("UPDATE runs SET cursor=?,pages=?,errors=?,status=? WHERE id=?", (next_url, pages, json.dumps(errors), "partial" if next_url else "completed", run_id))
                visited.add(cursor)
                cursor = next_url
        except Exception as exc:
            errors.append({"url": cursor, "message": str(exc), "type": type(exc).__name__})
            with self.store.db:
                self.store.db.execute("UPDATE runs SET status='failed',errors=? WHERE id=?", (json.dumps(errors), run_id))
            raise
        return {"run_id": run_id, "status": "partial" if cursor else "completed", "pages": pages,
                "rows": len(self.store.rows(run_id)), "errors": errors,
                "network_requests": self.network_requests, "cache_hits": self.cache_hits}


def export_rows(rows: list[dict], directory: str | Path) -> None:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    (path / "catalog.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with (path / "catalog.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "product_id", "product_name", "price", "currency", "source_url", "captured_at"])
        writer.writeheader()
        writer.writerows(rows)
