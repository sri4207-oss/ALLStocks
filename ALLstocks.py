import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="NSE Market Scanner (No API Key)", layout="wide")
st.title("📊 Live NSE Market Scanner (Free / No Login Required)")


@st.cache_data(ttl=300, show_spinner="Fetching live NSE equity data...")
def fetch_nse_all_stocks():
    """Fetches live NSE equity data including 52-week high/low directly from NSE public feed."""
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/live-equity-market",
    }

    try:
        # 1. Initialize session cookies from NSE homepage
        session.get("https://www.nseindia.com", headers=headers, timeout=10)

        # 2. Fetch NIFTY TOTAL MARKET (covers top ~750 NSE stocks with 52W High/Low)
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20TOTAL%20MARKET"
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        records = []
        for item in data:
            symbol = item.get("symbol", "")
            # Skip index summary row
            if not symbol or "NIFTY" in symbol:
                continue

            ltp = float(item.get("lastPrice", 0))
            if ltp <= 0:
                continue

            pct_change = float(item.get("pChange", 0))
            high_52w = float(item.get("yearHigh", 0))
            low_52w = float(item.get("yearLow", 0))
            volume = int(item.get("totalTradedVolume", 0))

            # Distance from 52W High & 52W Low
            dist_high_pct = ((high_52w - ltp) / high_52w * 100) if high_52w > 0 else 999
            dist_low_pct = ((ltp - low_52w) / low_52w * 100) if low_52w > 0 else 999

            records.append({
                "Symbol": symbol,
                "Company": item.get("meta", {}).get("companyName", symbol),
                "LTP (₹)": round(ltp, 2),
                "% Change": round(pct_change, 2),
                "Open": float(item.get("open", 0)),
                "Day High": float(item.get("dayHigh", 0)),
                "Day Low": float(item.get("dayLow", 0)),
                "Prev Close": float(item.get("previousClose", 0)),
                "52W High": round(high_52w, 2),
                "52W Low": round(low_52w, 2),
                "% Below 52W High": round(dist_high_pct, 2),
                "% Above 52W Low": round(dist_low_pct, 2),
                "Volume": volume,
            })

        return pd.DataFrame(records)

    except Exception as e:
        st.error(f"Error connecting to NSE feed: {e}")
        return pd.DataFrame()


# --- Sidebar Controls ---
with st.sidebar:
    st.header("Scanner Controls")
    if st.button("🔄 Refresh Live Data"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Data Source: NSE India Market Feed (No API key or token needed).")

market_df = fetch_nse_all_stocks()

if market_df.empty:
    st.warning("Could not load live NSE data right now (NSE servers may be temporarily blocking cloud IPs). Try refreshing in a minute.")
    st.stop()

# --- 5 Separate Tabs as Requested ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1️⃣ All Stocks (Small → High)",
    "2️⃣ Recent 52-Week High",
    "3️⃣ 52-Week Low (High Demand)",
    "4️⃣ Top Movers (+ Plus Side)",
    "5️⃣ Top Movers (- Minus Side)",
])

with tab1:
    st.subheader(f"All Stocks Sorted Low to High Price ({len(market_df)} Stocks)")
    st.dataframe(
        market_df.sort_values(by="LTP (₹)", ascending=True),
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.subheader("Stocks Near / At 52-Week High (Within 3% of 52W High)")
    recent_high_df = market_df[market_df["% Below 52W High"] <= 3.0].sort_values(
        by="% Below 52W High", ascending=True
    )
    st.dataframe(recent_high_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("52-Week Low Stocks with High Demand (Within 5% of 52W Low + High Volume)")
    near_low_df = market_df[market_df["% Above 52W Low"] <= 5.0].sort_values(
        by="Volume", ascending=False
    )
    st.dataframe(near_low_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("High Moving Ratio — Plus Side (Top Gainers)")
    plus_df = market_df[market_df["% Change"] > 0].sort_values(
        by="% Change", ascending=False
    )
    st.dataframe(plus_df, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("High Moving Ratio — Minus Side (Top Losers)")
    minus_df = market_df[market_df["% Change"] < 0].sort_values(
        by="% Change", ascending=True
    )
    st.dataframe(minus_df, use_container_width=True, hide_index=True)
