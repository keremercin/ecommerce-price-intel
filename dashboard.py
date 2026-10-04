"""Read-only dashboard: collection runs separately through the CLI."""
import httpx
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Catalog Observatory", page_icon="◈", layout="wide")
st.markdown("### CATALOG OBSERVATORY")
st.title("From web pages to traceable price data")
st.caption("Python ingestion · persistent observations · source-linked records · visible failures")
api_base = st.sidebar.text_input("API address", "http://127.0.0.1:8100").rstrip("/")
mode = st.sidebar.selectbox("Dataset", ["stored", "sample"])
threshold = st.sidebar.slider("Price change threshold (%)", 1.0, 30.0, 5.0)
st.sidebar.info("Stored: collected observations. Sample: synthetic movements for demonstrating alerts.")


def load(endpoint, **params):
    response = httpx.get(api_base + endpoint, params=params, timeout=10)
    response.raise_for_status()
    return response.json()["data"]


try:
    latest = pd.DataFrame(load("/v1/latest", mode=mode)["rows"])
    alert_data = load("/v1/alerts", mode=mode, pct_threshold=threshold)
    runs = pd.DataFrame(load("/v1/catalog/runs")["runs"])
    a, b, c, d = st.columns(4)
    a.metric("Products observed", len(latest))
    b.metric("Collection runs", len(runs))
    c.metric("Price alerts", alert_data["count"])
    d.metric("Dataset", "Collected" if mode == "stored" else "Synthetic")
    st.info("Books to Scrape is a public training catalog. Prices are synthetic; live collection demonstrates engineering, not market intelligence.")
    catalog, history, quality = st.tabs(["Catalog", "History & alerts", "Run quality"])
    with catalog:
        st.subheader("Every record has a source")
        if latest.empty:
            st.warning("No stored observations. Run: python scripts/collect_catalog.py --pages 3")
        else:
            search = st.text_input("Find a product")
            shown = latest[latest.product_name.str.contains(search, case=False, regex=False)] if search else latest
            columns = [x for x in ["product_name", "price", "currency", "source_url", "captured_at"] if x in shown]
            st.dataframe(shown[columns], hide_index=True, use_container_width=True,
                         column_config={"source_url": st.column_config.LinkColumn("Source")})
            st.download_button("Download catalog CSV", shown.to_csv(index=False), "catalog.csv", "text/csv")
    with history:
        st.subheader("Observed changes")
        if alert_data["alerts"]:
            st.dataframe(pd.DataFrame(alert_data["alerts"]), hide_index=True, use_container_width=True)
        else:
            st.caption("No price changes exceeded the threshold. Stable prices are a valid result.")
        endpoint = "/v1/catalog/history" if mode == "stored" else "/v1/sample-data"
        series = pd.DataFrame(load(endpoint)["rows"])
        if not series.empty:
            product = st.selectbox("Product history", sorted(series.product_name.unique()))
            selected = series[series.product_name == product].sort_values("captured_at")
            st.line_chart(selected.set_index("captured_at")[["price"]])
    with quality:
        st.subheader("Failures and progress stay visible")
        if not runs.empty:
            st.dataframe(runs[["started_at", "status", "pages", "cursor", "errors"]], hide_index=True, use_container_width=True)
        else:
            st.caption("No collection runs recorded.")
except (httpx.HTTPError, KeyError, ValueError) as exc:
    st.error(f"Could not load the catalog API: {exc}")
    st.code("uvicorn price_intel.api.main:app --host 127.0.0.1 --port 8100")
