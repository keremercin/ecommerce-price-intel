"""Run only against the explicitly permitted public scraping sandbox."""
import argparse
import json
from pathlib import Path

from price_intel.catalog import CatalogCrawler, CatalogStore, export_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=3)
    parser.add_argument("--database", default="data/catalog.db")
    parser.add_argument("--output", default="reports/catalog")
    parser.add_argument("--resume", help="Continue a partial or failed run ID")
    parser.add_argument("--refresh", action="store_true", help="Fetch new observations instead of cached HTML")
    args = parser.parse_args()
    store = CatalogStore(args.database)
    crawler = CatalogCrawler(store, cache_ttl=0 if args.refresh else 3600)
    try:
        report = crawler.crawl(max_pages=args.pages, run_id=args.resume)
        export_rows(store.rows(report["run_id"]), args.output)
        report["source_notice"] = "Live HTTP collection from Books to Scrape, a sandbox with synthetic prices; not commercial customer data."
        Path(args.output, "run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        crawler.close()
        store.close()


if __name__ == "__main__":
    main()
