# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import matplotlib.pyplot as plt
import requests_cache
from datetime import timedelta, datetime
import time
import warnings

warnings.filterwarnings("ignore")

# Cấu hình trang Streamlit
st.set_page_config(page_title="MF-TREND PRO V7.0", layout="wide")

# --- CSS tùy chỉnh để giao diện giống App ---
st.markdown("""
    <style>
    .main { background-color: #121212; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1f538d; color: white; }
    .stDataFrame { background-color: #1e1e1e; }
    [data-testid="stSidebar"] { background-color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# Cấu hình Cache dữ liệu
@st.cache_resource
def get_session():
    return requests_cache.CachedSession('yfinance_cache', expire_after=timedelta(minutes=30))

def calculate_indicators(df):
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
    # MF-Trend Indicators
    df['mfi'] = ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=14)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['adl'] = ta.ad(df['high'], df['low'], df['close'], df['volume'])
    adx_df = ta.adx(df['high'], df['low'], df['close'])
    df['adx_14'] = adx_df['ADX_14']
    
    # Alpha Strategy
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['sl_line'] = (df['close'].shift(1) - (atr.shift(1) * 2)).rolling(window=20, min_periods=1).max()
    df['ma20'] = df['close'].rolling(window=20).mean()
    return df

def check_signals(df):
    t0, t5, t20 = -1, -6, -21
    # Tiêu chí Xu hướng (ADX)
    c_adx = (df['adx_14'].iloc[t0] > 20) and (df['adx_14'].iloc[t0] > df['adx_14'].iloc[t5])
    # Tiêu chí Động lượng (MFI & RSI)
    c_mfi = (48 <= df['mfi'].iloc[t0] <= 68) and (df['mfi'].iloc[t0] > df['mfi'].iloc[t20])
    c_rsi = (48 <= df['rsi'].iloc[t0] <= 58) and (df['rsi'].iloc[t0] > df['rsi'].iloc[t20])
    # Tiêu chí Tích lũy (ADL)
    c_adl = df['adl'].iloc[t0] > df['adl'].iloc[t20]
    
    khuyen_nghi = "️🎖️ VÀO LỆNH" if (df['close'].iloc[t0] > df['sl_line'].iloc[t0] and df['close'].iloc[t0] > df['ma20'].iloc[t0]) else "❌ GÃY TREND"
    sig = "🔥 MUA CHÍNH" if (c_adx and c_mfi and c_rsi and c_adl) else "Theo dõi"
    
    return {
        "price": int(round(df['close'].iloc[t0])),
        "alpha_status": "BUY" if df['close'].iloc[t0] > df['ma20'].iloc[t0] else "SELL",
        "gap": f"{((df['close'].iloc[t0]/df['ma20'].iloc[t0])-1)*100:.1f}%",
        "sl": f"{int(round(df['sl_line'].iloc[t0])):,}",
        "recommend": khuyen_nghi,
        "adx": f"{df['adx_14'].iloc[t0]:.1f}",
        "mfi": f"{df['mfi'].iloc[t0]:.1f}",
        "rsi": f"{df['rsi'].iloc[t0]:.1f}",
        "flow": "Tích cực" if c_adl else "Yếu",
        "mf_signal": sig
    }

def draw_chart(symbol, df):
    fig = plt.figure(figsize=(12, 10), dpi=100)
    fig.patch.set_facecolor('#121212')
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.2)
    
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax4 = fig.add_subplot(gs[3], sharex=ax1)

    # Plot Price & Signals
    ax1.plot(df.index, df['close'], color='#00d4ff', label='Giá')
    ax1.plot(df.index, df['ma20'], color='#ffcc00', linestyle='--', label='MA20')
    ax1.plot(df.index, df['sl_line'], color='#e74c3c', linestyle=':', label='Stoploss')
    
    # Plot MFI/RSI/ADX
    ax2.plot(df.index, df['mfi'], color='#9b59b6', label='MFI')
    ax2.plot(df.index, df['rsi'], color='#f1c40f', label='RSI')
    ax3.plot(df.index, df['adx_14'], color='#e67e22', label='ADX')
    ax4.plot(df.index, df['adl'], color='#1abc9c', label='ADL')

    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_facecolor('#121212')
        ax.tick_params(colors='white')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.1)

    st.pyplot(fig)

# --- GIAO DIỆN SIDEBAR ---
st.sidebar.title("MF-TREND SYSTEM")
mode = st.sidebar.segmented_control("DANH MỤC", ["CÁ NHÂN", "THỊ TRƯỜNG"], default="CÁ NHÂN")

# Quản lý Watchlist đơn giản bằng Text Area
default_symbols = "SSI, HPG, FPT, VCI, MBB"
watchlist_str = st.sidebar.text_area("DANH SÁCH MÃ (Cách nhau bằng dấu phẩy)", default_symbols)
symbols = [s.strip().upper() for s in watchlist_str.split(",") if s.strip()]

filter_mode = st.sidebar.selectbox("BỘ LỌC NHANH", ["TẤT CẢ", "CHỈ CÓ TÍN HIỆU"])

if st.sidebar.button("BẮT ĐẦU QUÉT"):
    results = []
    progress_bar = st.progress(0)
    
    for i, s in enumerate(symbols):
        try:
            df = yf.download(f"{s}.VN", period="8mo", progress=False)
            if df.empty: continue
            df = calculate_indicators(df)
            res = check_signals(df)
            res['symbol'] = s
            results.append(res)
            progress_bar.progress((i + 1) / len(symbols))
        except: continue
    
    st.session_state['full_results'] = results

# --- HIỂN THỊ KẾT QUẢ ---
if 'full_results' in st.session_state:
    df_res = pd.DataFrame(st.session_state['full_results'])
    
    if filter_mode == "CHỈ CÓ TÍN HIỆU":
        df_res = df_res[(df_res['recommend'].str.contains("VÀO")) | (df_res['mf_signal'].str.contains("MUA"))]

    st.subheader("1. CHIẾN LƯỢC ALPHA TREND")
    st.dataframe(df_res[['symbol', 'price', 'alpha_status', 'gap', 'sl', 'recommend']], use_container_width=True)

    st.subheader("2. ĐỘNG LƯỢNG & TÍCH LŨY (MF-TREND)")
    st.dataframe(df_res[['symbol', 'adx', 'mfi', 'rsi', 'flow', 'mf_signal']], use_container_width=True)

    # Chọn mã để xem biểu đồ
    st.divider()
    selected_stock = st.selectbox("CHỌN MÃ XEM BIỂU ĐỒ CHI TIẾT", symbols)
    if st.button("HIỆN BIỂU ĐỒ"):
        df_chart = yf.download(f"{selected_stock}.VN", period="8mo", progress=False)
        df_chart = calculate_indicators(df_chart)
        draw_chart(selected_stock, df_chart)