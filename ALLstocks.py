import io
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="All NSE Stocks Scanner", layout="wide")
st.title("📈 All NSE Stocks Scanner (Streamlit Edition)")


@st.cache_data(ttl=86400, show_spinner="Loading official NSE stock list...")
def get_all_nse_symbols():
    """Downloads the official list of all ~2,000+ NSE EQ stocks."""
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = [c.strip() for c in df.columns]
        df = df[df["SERIES"] == "EQ"].copy()
        return df[["SYMBOL", "NAME OF COMPANY"]].rename(
            columns={"SYMBOL": "Symbol", "NAME OF COMPANY": "Company"}
        )
    except Exception:
        # Fallback list of major + smallcap NSE symbols if NSE archive times out
        fallback = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
            "ITC", "LT", "HINDUNILVR", "BAJFINANCE", "MARUTI", "TATAMOTORS", "SUNPHARMA",
            "AXISBANK", "TITAN", "ADANIENT", "NTPC", "ONGC", "POWERGRID", "WIPRO",
            "ULTRACEMCO", "JSWSTEEL", "TATASTEEL", "M&M", "COALINDIA", "HCLTECH",
            "ASIANPAINT", "ZOMATO", "SUZLON", "YESBANK", "IDEA", "IRFC", "RVNL",
            "NHPC", "SJVN", "BEL", "HAL", "TRENT", "VBL", "PNB", "BANKBARODA",
            "CANBK", "IDFCFIRSTB", "FEDERALBNK", "ASHOKLEY", "BHEL", "SAIL", "NMDC",
            "AGL", "ALLCARGO", "JPPOWER", "RPOWER", "GTLINFRA", "VODAFONE", "UCOBANK",
        ]
        return pd.DataFrame({"Symbol": fallback, "Company": fallback})


@st.cache_data(ttl=600, show_spinner="Fetching live & 52-week market data...")
def fetch_market_snapshot(symbols_df, max_stocks):
    """Fetches 1-year daily data in batches to compute LTP, % Change, 52W High & 52W Low."""
    subset = symbols_df.head(max_stocks).copy()
    name_map = dict(zip(subset["Symbol"], subset["Company"]))
    tickers = [f"{sym}.NS" for sym in subset["Symbol"]]

    # Batch download 1 year of daily candles (fast, avoids rate limits)
    raw = yf.download(
        tickers=tickers,
        period="1y",
        interval="1d",
        group_by="ticker",
        threads=True,
        progress=False,
    )

    records = []
    for sym in subset["Symbol"]:
        ticker = f"{sym}.NS"
        try:
            df_t = raw[ticker] if len(tickers) > 1 else raw
            df_t = df_t.dropna(subset=["Close"])
            if len(df_t) < 2:
                continue

            ltp = float(df_t["Close"].iloc[-1])
            prev_close = float(df_t["Close"].iloc[-2])
            open_p = float(df_t["Open"].iloc[-1])
            day_high = float(df_t["High"].iloc[-1])
            day_low = float(df_t["Low"].iloc[-1])
            volume = int(df_t["Volume"].iloc[-1])
            avg_vol_10d = float(df_t["Volume"].tail(10).mean())

            high_52w = float(df_t["High"].max())
            low_52w = float(df_t["Low"].min())

            pct_change = ((ltp - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
            dist_high_pct = ((high_52w - ltp) / high_52w * 100) if high_52w > 0 else 999.0
            dist_low_pct = ((ltp - low_52w) / low_52w * 100) if low_52w > 0 else 999.0
            vol_spike = round(volume / avg_vol_10d, 2) if avg_vol_10d > 0 else 0.0

            records.append({
                "Symbol": sym,
                "Company": name_map.get(sym, sym),
                "LTP (₹)": round(ltp, 2),
                "% Change": round(pct_change, 2),
                "Open": round(open_p, 2),
                "Day High": round(day_high, 2),
                "Day Low": round(day_low, 2),
                "Prev Close": round(prev_close, 2),
                "52W High": round(high_52w, 2),
                "52W Low": round(low_52w, 2),
                "% Below 52W High": round(dist_high_pct, 2),
                "% Above 52W Low": round(dist_low_pct, 2),
                "Volume": volume,
                "Volume Surge (x)": vol_spike,
            })
        except Exception:
            continue

    return pd.DataFrame(records)


# --- Sidebar Controls ---
all_symbols_df = get_all_nse_symbols()

with st.sidebar:
    st.header("Scanner Settings")
    st.write(f"Total NSE Stocks Available: **{len(all_symbols_df)}**")
    stock_limit = st.slider(
        "Number of NSE stocks to load",
        min_value=100,
        max_value=min(1000, len(all_symbols_df)),
        value=300,
        step=50,
        help="300 stocks loads in ~10 seconds. Increase up to 1,000 for a wider scan.",
    )
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

market_df = fetch_market_snapshot(all_symbols_df, stock_limit)

if market_df.empty:
    st.error("No stock data returned. Click 'Refresh Data' in the sidebar.")
    st.stop()

# --- 5 Separate Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1️⃣ All Stocks (Small → High)",
    "2️⃣ Recent 52-Week High",
    "3️⃣ 52-Week Low (High Demand)",
    "4️⃣ Top Movers (+ Plus Side)",
    "5️⃣ Top Movers (- Minus Side)",
])

with tab1:
    st.subheader(f"All Loaded NSE Stocks Sorted Small to High Price ({len(market_df)} Stocks)")
    st.dataframe(
        market_df.sort_values(by="LTP (₹)", ascending=True),
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.subheader("Recent 52-Week High Stocks (Within 3% of 52W High)")
    high_52w_df = market_df[market_df["% Below 52W High"] <= 3.0].sort_values(
        by="% Below 52W High", ascending=True
    )
    st.dataframe(high_52w_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("52-Week Low Stocks in High Demand (Within 5% of 52W Low + High Volume)")
    low_demand_df = market_df[market_df["% Above 52W Low"] <= 5.0].sort_values(
        by=["Volume Surge (x)", "Volume"], ascending=[False, False]
    )
    st.dataframe(low_demand_df, use_container_width=True, hide_index=True)

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
