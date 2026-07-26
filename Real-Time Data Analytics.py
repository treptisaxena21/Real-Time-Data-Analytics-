#Libraries required
import time
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# config dashboard
st.set_page_config(
    page_title="Real-Time Analytics Dashboard",
    page_icon="🚀",
    layout="wide",
)
st.markdown("""
<style>

/* Main App Background */
.stApp {
    background: linear-gradient(135deg, #0f172a, #1e293b, #0f172a);
    color: white;
}

/* Sidebar */
[data-testid="stSidebar"]{
    background: linear-gradient(180deg,#111827,#1f2937);
}

/* Title */
h1{
    color:#38bdf8;
    text-align:center;
    font-weight:bold;
}

/* Sub Headers */
h2,h3{
    color:#7dd3fc;
}

/* Metric Cards */
div[data-testid="stMetric"]{
    background: rgba(255,255,255,0.08);
    border:1px solid rgba(255,255,255,0.15);
    padding:18px;
    border-radius:15px;
    box-shadow:0 4px 12px rgba(0,0,0,0.3);
}

/* DataFrame */
[data-testid="stDataFrame"]{
    border-radius:12px;
    overflow:hidden;
}

/* Tabs */
button[data-baseweb="tab"]{
    font-size:16px;
    font-weight:bold;
    color:white;
}

button[data-baseweb="tab"][aria-selected="true"]{
    background:#0ea5e9;
    color:white;
    border-radius:10px;
}

/* Buttons */
.stButton>button{
    background:#0ea5e9;
    color:white;
    border-radius:10px;
    border:none;
}


.stTextInput input,
.stNumberInput input{
    background:#1e293b;
    color:white;
}

/* Select Boxes */
.stSelectbox div[data-baseweb="select"]{
    background:#1e293b;
}

/* Slider */
.stSlider{
    color:#38bdf8;
}

</style>"""
, unsafe_allow_html=True)


if "crypto_history" not in st.session_state:
    st.session_state.crypto_history = pd.DataFrame(
        columns=["timestamp", "coin", "price_usd"]
    )
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()


# Fetching live cryptocurrency data
@st.cache_data(ttl=25)
def fetch_crypto_prices(coin_ids: list[str], vs_currency: str = "usd") -> pd.DataFrame:
    """
    Fetch live crypto prices from CoinGecko (no API key required).
    Docs: https://www.coingecko.com/en/api/documentation
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": vs_currency,
        "include_24hr_change": "true",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"Crypto API error: {e}")
        return pd.DataFrame()

    rows = []
    now = datetime.now()
    for coin, values in data.items():
        rows.append(
            {
                "timestamp": now,
                "coin": coin,
                "price_usd": round(values.get(vs_currency, 0), 2),
                "change_24h_pct": round(values.get(f"{vs_currency}_24h_change", 0), 2),
            }
        )
    return pd.DataFrame(rows)

# Fetching Live weather
@st.cache_data(ttl=60)
def fetch_weather(city: str, api_key: str) -> dict | None:
    """
    Fetch live weather from OpenWeatherMap (requires free API key).
    Docs: https://openweathermap.org/current
    """
    if not api_key:
        return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"Weather API error for {city}: {e}")
        return None

    return {
        "city": city,
        "temp_c": data["main"]["temp"],
        "feels_like_c": data["main"]["feels_like"],
        "humidity_pct": data["main"]["humidity"],
        "condition": data["weather"][0]["description"].title(),
        "timestamp": datetime.now(),
    }

# Fetching live stock price
@st.cache_data(ttl=300)
def fetch_stock_price(symbol: str, api_key: str) -> dict | None:
    """
    Fetch live stock price from Alpha Vantage (requires free API key).
    Docs: https://www.alphavantage.co/documentation/#latestprice
    """
    if not api_key:
        return None
    url = "https://www.alphavantage.co/query"
    params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("Global Quote", {})
    except Exception as e:
        st.error(f"Stock API error for {symbol}: {e}")
        return None

    if not data:
        return None

    return {
        "symbol": symbol,
        "price": float(data.get("05. price", 0)),
        "change_pct": data.get("10. change percent", "0%").replace("%", ""),
        "timestamp": datetime.now(),
    }

st.sidebar.title("⚙️ Dashboard Settings")

st.sidebar.subheader("🪙 Crypto")
#allow user to choose cryptocurrencies
available_coins = ["bitcoin", "ethereum", "dogecoin", "solana", "cardano", "ripple"]
selected_coins = st.sidebar.multiselect(
    "Select coins to track", available_coins, default=["bitcoin", "ethereum"]
)
#Set Alert
crypto_alert_threshold = st.sidebar.number_input(
    "🔔 Alert if any selected coin price crosses (USD)",
    min_value=0.0,
    value=100000.0,
    step=100.0,
)

st.sidebar.subheader("🌦️ Weather (optional)")
owm_api_key = st.sidebar.text_input("OpenWeatherMap API key", type="password")
cities = st.sidebar.text_input("Cities (comma-separated)", "Ludhiana,London,New York")
city_list = [c.strip() for c in cities.split(",") if c.strip()]

st.sidebar.subheader("📈 Stocks (optional)")
av_api_key = st.sidebar.text_input("Alpha Vantage API key", type="password")
stock_symbols_input = st.sidebar.text_input("Stock symbols (comma-separated)", "AAPL,MSFT")
stock_symbols = [s.strip().upper() for s in stock_symbols_input.split(",") if s.strip()]

st.sidebar.subheader("🔄 Auto-Refresh")
auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 10, 120, 30)


st.title("📊 Real-Time Data Analytics Dashboard")
st.caption(
    f"Last updated: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}  |  "
    f"Auto-refresh: {'ON — every ' + str(refresh_interval) + 's' if auto_refresh else 'OFF'}"
)

tab_crypto, tab_weather, tab_stocks = st.tabs(["🪙 Crypto", "🌦️ Weather", "📈 Stocks"])

#  CRYPTO TAB
with tab_crypto:
    if not selected_coins:
        st.info("Select at least one coin from the sidebar to see live data.")
    else:
        df = fetch_crypto_prices(selected_coins)

        if not df.empty:

            st.session_state.crypto_history = pd.concat(
                [st.session_state.crypto_history, df[["timestamp", "coin", "price_usd"]]],
                ignore_index=True,
            ).tail(500)

            crossed = df[df["price_usd"] >= crypto_alert_threshold]
            if not crossed.empty:
                for _, row in crossed.iterrows():
                    st.warning(
                        f"🚨 ALERT: **{row['coin'].capitalize()}** crossed your threshold "
                        f"of ${crypto_alert_threshold:,.2f} — current price ${row['price_usd']:,.2f}"
                    )


            cols = st.columns(len(df))
            for col, (_, row) in zip(cols, df.iterrows()):
                col.metric(
                    label=row["coin"].capitalize(),
                    value=f"${row['price_usd']:,.2f}",
                    delta=f"{row['change_24h_pct']}% (24h)",
                )


            st.subheader("Live Prices")
            st.dataframe(df, use_container_width=True, hide_index=True)


            st.subheader("Price Trend (this session)")
            hist = st.session_state.crypto_history
            if len(hist) > 1:
                pivot = hist.pivot_table(
                    index="timestamp", columns="coin", values="price_usd", aggfunc="last"
                )
                st.line_chart(pivot)
            else:
                st.caption("Trend chart will build up as more data points are collected.")

with tab_weather:
    if not owm_api_key:
        st.info(
            "Enter a free OpenWeatherMap API key in the sidebar to enable this tab. "
            "Get one at https://openweathermap.org/api"
        )
    else:
        weather_rows = []
        for city in city_list:
            w = fetch_weather(city, owm_api_key)
            if w:
                weather_rows.append(w)

        if weather_rows:
            cols = st.columns(len(weather_rows))
            for col, w in zip(cols, weather_rows):
                col.metric(
                    label=f"{w['city']} — {w['condition']}",
                    value=f"{w['temp_c']:.1f}°C",
                    delta=f"feels like {w['feels_like_c']:.1f}°C",
                )
                col.caption(f"Humidity: {w['humidity_pct']}%")

            st.subheader("Details")
            st.dataframe(pd.DataFrame(weather_rows), use_container_width=True, hide_index=True)

with tab_stocks:
    if not av_api_key:
        st.info(
            "Enter a free Alpha Vantage API key in the sidebar to enable this tab. "
            "Get one at https://www.alphavantage.co/support/#api-key\n\n"
            "Note: free tier allows only 25 requests/day, so this tab refreshes at most every 5 minutes."
        )
    else:
        stock_rows = []
        for sym in stock_symbols:
            s = fetch_stock_price(sym, av_api_key)
            if s:
                stock_rows.append(s)

        if stock_rows:
            cols = st.columns(len(stock_rows))
            for col, s in zip(cols, stock_rows):
                col.metric(
                    label=s["symbol"],
                    value=f"${s['price']:,.2f}",
                    delta=f"{s['change_pct']}%",
                )
            st.subheader("Details")
            st.dataframe(pd.DataFrame(stock_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("No stock data returned — check your symbols or API key/quota.")

if auto_refresh:
    st.session_state.last_refresh = datetime.now()
    time.sleep(refresh_interval)
    st.rerun()