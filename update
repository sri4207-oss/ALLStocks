import streamlit as st
import yfinance as yf

INDICES = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "NIFTY MIDCAP 100": "^CRSMID",
}

@st.cache_data(ttl=15)
def fetch_live_indices():
    results = []
    for name, symbol in INDICES.items():
        try:
            info = yf.Ticker(symbol).fast_info
            price = info.last_price
            prev_close = info.previous_close
            change = price - prev_close
            change_pct = (change / prev_close) * 100
            results.append({
                "name": name,
                "price": price,
                "change": change,
                "change_pct": change_pct,
            })
        except Exception:
            results.append({
                "name": name,
                "price": None,
                "change": 0.0,
                "change_pct": 0.0,
            })
    return results

def show_live_indices_bar():
    header_col, btn_col = st.columns([4, 1])
    header_col.subheader("Live Market Indices")
    if btn_col.button("Refresh Indices"):
        fetch_live_indices.clear()

    cols = st.columns(4)
    for col, idx in zip(cols, fetch_live_indices()):
        if idx["price"] is not None:
            col.metric(
                label=idx["name"],
                value=f"{idx['price']:,.2f}",
                delta=f"{idx['change']:+.2f} ({idx['change_pct']:+.2f}%)",
            )
        else:
            col.metric(label=idx["name"], value="Unavailable")

show_live_indices_bar()
