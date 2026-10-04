# Current architecture

The CLI collector (`src/price_intel/catalog.py`, `scripts/collect_catalog.py`) checks the configured HTTPS origin and robots policy, discovers pages, parses HTML/JSON-LD, validates records and commits run progress plus source-linked snapshots to SQLite. It uses bounded streaming, retries and response caching.

The API (`src/price_intel/api/main.py`) reads SQLite by default. Explicit sample mode returns hard-coded demonstration data. The dashboard unwraps the API envelope and displays catalog/history/run diagnostics. It does not collect arbitrary URLs.

Run and snapshot persistence supports local inspection and sequential resume. There is no distributed scheduler or cross-store product matching. See README for exact commands and tests.
