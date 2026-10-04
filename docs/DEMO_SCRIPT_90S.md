# Current catalog demo

1. Install the project and run `python scripts/collect_catalog.py --pages 3`.
2. Start the API on port 8100 and `streamlit run dashboard.py --server.port 8502`.
3. Select stored mode. Show product names, prices and source URLs.
4. Open Run quality: a three-page bounded run is partial, not a complete catalog scan.
5. Explain that the HTTP extraction is real but Books to Scrape prices are synthetic.
6. Switch to sample only to illustrate synthetic price movements. Do not imply observed market changes.

Evidence: the real screenshot is `output/playwright/catalog.png`; the recorded source-linked data are in `reports/catalog/`. This is a local engineering demonstration, not a production service/customer case study.
