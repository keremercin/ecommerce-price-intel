import json

import httpx
import pytest

from price_intel.catalog import (
    SOURCE,
    CatalogCrawler,
    CatalogStore,
    canonical_url,
    parse_catalog,
)


def page(name="Book", price="12.30", next_path=None):
    body = f'<article class="product_pod"><h3><a href="catalogue/book/index.html" title="{name}">book</a></h3><p class="price_color">£{price}</p></article>'
    if next_path:
        body += f'<li class="next"><a href="{next_path}">next</a></li>'
    return body


def crawler(tmp_path, handler):
    store = CatalogStore(tmp_path / "catalog.db")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return store, CatalogCrawler(store, client=client, delay=0, sleep=lambda _: None)


def test_parse_deduplicates_and_records_bad_cards():
    rows, _, errors = parse_catalog(page() + page() + page(price="NaN"), SOURCE + "/")
    assert len(rows) == 1
    assert rows[0]["price"] == 12.3
    assert rows[0]["currency"] == "GBP"
    assert errors == ["Invalid HTML product card"]


def test_jsonld_graph_and_offsite_pagination():
    product = {"@graph": [{"@type": "Product", "name": "  Nice   Book ", "url": "/book", "offers": {"price": "7.25", "priceCurrency": "GBP"}}]}
    html = f'<script type="application/ld+json">{json.dumps(product)}</script><a rel="next" href="https://evil.test/">next</a>'
    rows, nxt, errors = parse_catalog(html, SOURCE + "/")
    assert rows[0]["product_name"] == "Nice Book"
    assert nxt is None
    assert errors == ["Rejected next-page URL"]


@pytest.mark.parametrize("url", ["http://books.toscrape.com/", "https://evil.test/", "https://books.toscrape.com@evil.test/"])
def test_origin_boundary(url):
    with pytest.raises(ValueError):
        canonical_url(SOURCE, url, SOURCE)


def test_resume_and_cached_replay(tmp_path):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(200, text=page(next_path="/page2") if request.url.path == "/" else page("Second").replace("catalogue/book", "catalogue/second"))
    store, c = crawler(tmp_path, handler)
    first = c.crawl(max_pages=1)
    assert first["status"] == "partial"
    second = c.crawl(max_pages=1, run_id=first["run_id"])
    assert second["status"] == "completed"
    assert second["rows"] == 2
    before = c.network_requests
    replay = c.crawl(max_pages=2)
    assert replay["rows"] == 2
    assert c.network_requests == before
    assert len(store.rows()) == 4
    store.close()


def test_retry_and_fail_closed_robots(tmp_path):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, text="User-agent: *\nDisallow: /")
    store, c = crawler(tmp_path, handler)
    with pytest.raises(ValueError, match="disallows"):
        c.crawl()
    assert calls == [SOURCE + "/robots.txt"] * 2
    assert store.runs()[0]["status"] == "failed"
    store.close()


def test_failed_page_retains_cursor_for_resume(tmp_path):
    broken = True
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/page2" and broken:
            return httpx.Response(200, text="layout changed")
        return httpx.Response(200, text=page(next_path="/page2") if request.url.path == "/" else page().replace("catalogue/book", "catalogue/second"))
    store, c = crawler(tmp_path, handler)
    with pytest.raises(ValueError, match="No valid products"):
        c.crawl(max_pages=2)
    state = store.runs()[0]
    assert state["pages"] == 1 and state["cursor"].endswith("/page2")
    broken = False
    c.cache_ttl = 0
    result = c.crawl(run_id=state["id"])
    assert result["rows"] == 2 and result["status"] == "completed"
    store.close()

def test_duplicate_products_do_not_erase_visited_pages(tmp_path):
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        return httpx.Response(200, text=page(next_path='/page2' if request.url.path == '/' else '/'))
    store, c = crawler(tmp_path, handler)
    first = c.crawl(max_pages=2)
    assert first['rows'] == 1
    with pytest.raises(ValueError, match='Pagination loop'):
        c.crawl(run_id=first['run_id'])
    assert store.runs()[0]['pages'] == 2
    store.close()


def test_offsite_next_page_cannot_report_success(tmp_path):
    store, c = crawler(tmp_path, lambda request: httpx.Response(404) if request.url.path == '/robots.txt' else httpx.Response(200, text=page(next_path='https://evil.test/')))
    with pytest.raises(ValueError, match='pagination is incomplete'):
        c.crawl()
    assert store.runs()[0]['status'] == 'failed'
    store.close()


def test_jsonld_missing_identity_is_not_collapsed_into_page_product():
    items = [{'@type': None}, {'@type': 'Product', 'name': 'A', 'offers': {'price': '1', 'priceCurrency': 'GBP'}}]
    rows, _, errors = parse_catalog('<script type="application/ld+json">' + json.dumps(items) + '</script>', SOURCE + '/')
    assert rows == []
    assert errors == ['Invalid JSON-LD product/offer']


def test_oversize_stream_is_closed_and_never_cached(tmp_path):
    class LargeStream(httpx.SyncByteStream):
        def __init__(self):
            self.reads = 0
            self.closed = False
        def __iter__(self):
            for _ in range(100):
                self.reads += 1
                yield b'x' * 65536
        def close(self):
            self.closed = True
    stream = LargeStream()
    store, c = crawler(tmp_path, lambda request: httpx.Response(200, stream=stream))
    with pytest.raises(ValueError, match='2 MB'):
        c.fetch(SOURCE + '/large')
    assert stream.closed
    assert stream.reads < 100
    assert store.db.execute('SELECT COUNT(*) FROM cache').fetchone()[0] == 0
    store.close()
