import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="PRO AI TRADER", layout="wide")

st.title("📊 PRO AI TRADING DASHBOARD")
st.write("Smart trading system (ATR + AI Score)")

# -----------------------------
# INPUT
# -----------------------------
stocks_input = st.text_area(
    "Enter Stocks (one per line)",
    "RELIANCE\nTCS\nINFY\nHDFCBANK\nITC\nBHEL"
)

stocks = [s.strip().upper() for s in stocks_input.split("\n") if s.strip()]

# -----------------------------
# FETCH FUNCTION (SMART FIX)
# -----------------------------
def fetch_stock_data(symbol):
    try:
        # Try as-is
        data = yf.download(symbol, period="15d", interval="1d", progress=False)

        # Retry with .NS if needed
        if data.empty and not symbol.endswith(".NS"):
            symbol = symbol + ".NS"
            data = yf.download(symbol, period="15d", interval="1d", progress=False)

        return data, symbol

    except:
        return None, symbol

# -----------------------------
# ATR FUNCTION
# -----------------------------
def calculate_atr(data):
    high = data["High"]
    low = data["Low"]
    close = data["Close"]

    if isinstance(close, pd.DataFrame):
        high = high.iloc[:, 0]
        low = low.iloc[:, 0]
        close = close.iloc[:, 0]

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(5).mean()

    return atr.iloc[-1]

# -----------------------------
# SCANNER
# -----------------------------
if st.button("🚀 Run PRO Scanner"):

    results = []

    for stock in stocks:

        status = "OK"
        price = "-"
        signal = "-"
        target = "-"
        stoploss = "-"
        score = 0

        try:
            data, fixed_symbol = fetch_stock_data(stock)

            if data is None or data.empty:
                status = "No Data ❌"
            else:
                close = data["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]

                price = float(close.iloc[-1])

                returns = close.pct_change().dropna()
                avg_return = returns.mean()

                # SIGNAL
                signal = "BUY 📈" if avg_return > 0 else "SELL 📉"

                # ATR
                atr = calculate_atr(data)

                if pd.isna(atr):
                    status = "ATR Error"
                else:
                    # TARGET & STOPLOSS
                    if signal == "BUY 📈":
                        target = price + (2 * atr)
                        stoploss = price - atr
                    else:
                        target = price - (2 * atr)
                        stoploss = price + atr

                    target = round(target, 2)
                    stoploss = round(stoploss, 2)

                    # SCORE
                    score = round(abs(avg_return) * 1000, 2)

        except Exception as e:
            status = "Error"

        results.append({
            "Stock": stock,
            "Price": price,
            "Signal": signal,
            "Target": target,
            "Stoploss": stoploss,
            "Score": score,
            "Status": status
        })

    df = pd.DataFrame(results)

    # Sort best trades on top
    df = df.sort_values(by="Score", ascending=False)

    st.success("✅ Scan Complete")
    st.dataframe(df, use_container_width=True)

# -----------------------------
# CHART SECTION
# -----------------------------
st.subheader("📈 Chart")

selected = st.text_input("Enter stock", "RELIANCE")

if st.button("Show Chart"):
    try:
        chart, fixed = fetch_stock_data(selected)

        if chart is None or chart.empty:
            st.error("No chart data")
        else:
            close = chart["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            st.line_chart(close)

    except:
        st.error("Chart error")

# -----------------------------
# PCR SECTION
# -----------------------------
st.subheader("📊 NIFTY PCR")

def get_pcr():
    try:
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        headers = {"User-Agent": "Mozilla/5.0"}

        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)

        response = session.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            records = data["records"]["data"]

            ce_total = 0
            pe_total = 0

            for item in records:
                ce_total += item.get("CE", {}).get("openInterest", 0)
                pe_total += item.get("PE", {}).get("openInterest", 0)

            if ce_total > 0:
                return pe_total / ce_total

        return None

    except:
        return None

pcr = get_pcr()

if pcr:
    st.metric("PCR", round(pcr, 2))

    if pcr > 1:
        st.success("Bullish 🟢")
    else:
        st.error("Bearish 🔴")
else:
    st.warning("PCR not available")