import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Ecommerce Price Intel", layout="wide")
st.title("🛒 Ecommerce Price Intel")

api_base = st.sidebar.text_input("API Base", value="http://localhost:8100")
threshold = st.sidebar.slider("Alert % threshold", min_value=1.0, max_value=30.0, value=5.0)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Latest Prices")
    if st.button("Load Latest"):
        r = requests.get(f"{api_base}/v1/latest", timeout=15)
        if r.ok:
            df = pd.DataFrame(r.json()["rows"])
            st.dataframe(df[["product_name", "price", "currency", "captured_at"]], use_container_width=True)
            if not df.empty:
                st.bar_chart(df.set_index("product_name")["price"])
        else:
            st.error(r.text)

with col2:
    st.subheader("Price Alerts")
    if st.button("Load Alerts"):
        r = requests.get(f"{api_base}/v1/alerts", params={"pct_threshold": threshold}, timeout=15)
        if r.ok:
            payload = r.json()
            alerts = pd.DataFrame(payload["alerts"])
            st.metric("Alert count", payload["count"])
            if alerts.empty:
                st.info("No alerts at current threshold")
            else:
                st.dataframe(alerts, use_container_width=True)
        else:
            st.error(r.text)

st.subheader("Raw Time Series")
if st.button("Load Raw Series"):
    r = requests.get(f"{api_base}/v1/sample-data", timeout=15)
    if r.ok:
        df = pd.DataFrame(r.json()["rows"])
        st.dataframe(df, use_container_width=True)
    else:
        st.error(r.text)
