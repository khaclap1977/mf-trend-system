# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings("ignore")

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="MF-Trend Gold Mobile", layout="wide")

# --- HÀM TÍNH ALPHA TREND (Logic cốt lõi từ MFTrend.py) ---
def calculate_alpha_trend(df, period=14, coeff=2.5):
    """Tính toán đường chặn dưới Alpha Trend"""
    df = df.copy()
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    up_t = df['low'] - atr * coeff
    down_t = df['high'] + atr * coeff
    
    alpha_trend = np.zeros(len(df))
    for i in range(1, len(df)):
        if df['mfi'].iloc[i] > 50:
            alpha_trend[i] = max(up_t.iloc[i], alpha_trend[i-1])
        else:
            alpha_trend[i] = min(down_t.iloc[i], alpha_trend[i-1] if alpha_trend[i-1] != 0 else down_t.iloc[i])
    df['alpha_trend'] = alpha_trend
    return df

# --- ĐỌC DỮ LIỆU TỐI ƯU TỪ FILE GOLD.XLSX ---
def load_gold_settings():
    try:
        # Cần thư viện openpyxl trong requirements.txt
        df_gold = pd.read_excel("GOLD.xlsx") 
        # Sử dụng cột 'Ticker' làm khóa tra cứu từ file của bạn
        return df_gold.set_index('Ticker').to_dict('index')
    except Exception as e:
        st.error(f"⚠️ Lỗi đọc file GOLD.xlsx: {e}")
        return {}

def process_data(symbol):
    """Tải và tính toán toàn bộ chỉ báo kỹ thuật"""
    try:
        df = yf.download(f"{symbol}.VN", period="1y", progress=False)
        if df.empty: return None
        df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        
        # Chỉ báo động lượng & tích lũy
        df['mfi'] = ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=14)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['adl'] = ta.ad(df['high'], df['low'], df['close'], df['volume'])
        adx_df = ta.adx(df['high'], df['low'], df['close'])
        df['adx'] = adx_df['ADX_14']
        
        # Alpha Trend & MA20
        df = calculate_alpha_trend(df)
        df['ma20'] = df['close'].rolling(window=20).mean()
        return df
    except: return None

def scan_with_tolerance(s, df, gold_settings):
    """Quét dựa trên tham số tối ưu và Tolerance 4%"""
    t0, t5, t20 = -1, -6, -21
    
    # Lấy thông số tối ưu riêng cho mã s từ file GOLD
    opt = gold_settings.get(s, {'ADX_Min': 20, 'RSI_Buy': 48, 'MFI_Buy': 48})
    tolerance = 0.04  # Ngưỡng sai số 4% cố định theo yêu cầu
    
    # 1. Điều kiện ADX: t0 >= ADX_Min (có tolerance) và t0 > t5 [cite: 2025-12-08]
    c_adx = (df['adx'].iloc[t0] >= opt['ADX_Min'] * (1 - tolerance)) and (df['adx'].iloc[t0] > df['adx'].iloc[t5])
    
    # 2. Điều kiện MFI/RSI: Hội tụ với ngưỡng tối ưu [cite: 2025-12-09]
    c_mfi = (df['mfi'].iloc[t0] >= opt['MFI_Buy'] * (1 - tolerance)) and (df['mfi'].iloc[t0] > df['mfi'].iloc[t20])
    c_rsi = (df['rsi'].iloc[t0] >= opt['RSI_Buy'] * (1 - tolerance)) and (df['rsi'].iloc[t0] > df['rsi'].iloc[t20])
    
    # 3. Điều kiện Alpha: Giá nằm trên Alpha Trend
    c_alpha = df['close'].iloc[t0] > df['alpha_trend'].iloc[t0]
    
    # ĐIỂM VÀNG HỘI TỤ
    is_gold = c_adx and c_mfi and c_rsi and c_alpha
    
    return {
        "Mã": s,
        "Giá": f"{df['close'].iloc[t0]:,.0f}",
        "ADX": f"{df['adx'].iloc[t0]:.1f}",
        "MFI": f"{df['mfi'].iloc[t0]:.1f}",
        "RSI": f"{df['rsi'].iloc[t0]:.1f}",
        "Tín hiệu": "🔥 ĐIỂM VÀNG" if is_gold else "---",
        "Chiến thuật": "MUA 1/3 (P1)" if is_gold else "Quan sát",
        "is_gold_sort": 1 if is_gold else 0
    }

# --- GIAO DIỆN MOBILE ---
st.title("🛡️ MF-TREND GOLD OPTIMIZER")

gold_params = load_gold_settings()

if st.button("🚀 BẮT ĐẦU QUÉT ĐIỂM VÀNG (TOLERANCE 4%)"):
    if not gold_params:
        st.warning("Vui lòng kiểm tra file GOLD.xlsx trên GitHub.")
    else:
        results = []
        symbols = list(gold_params.keys())
        progress = st.progress(0)
        
        for i, s in enumerate(symbols):
            data = process_data(s)
            if data is not None:
                results.append(scan_with_tolerance(s, data, gold_params))
            progress.progress((i + 1) / len(symbols))
            
        if results:
            df_res = pd.DataFrame(results)
            # Sắp xếp: Mã có Điểm Vàng hiện lên trên cùng
            df_res = df_res.sort_values(by="is_gold_sort", ascending=False).drop(columns=['is_gold_sort'])
            
            st.subheader("Bảng Tín Hiệu Hội Tụ")
            st.dataframe(df_res.style.apply(lambda x: ['background-color: #ffd700; color: black' if x['Tín hiệu'] == "🔥 ĐIỂM VÀNG" else '' for _ in x], axis=1), use_container_width=True)
            
            st.info("💡 Giải ngân 1/3 số vốn (20-25% NAV) khi đạt Điểm Vàng [cite: 2025-12-09].")

# --- BIỂU ĐỒ SOI CHI TIẾT ---
st.divider()
selected = st.selectbox("Soi Chart mã:", list(gold_params.keys()) if gold_params else [])
if st.button("📊 HIỆN CHART"):
    df_plot = process_data(selected)
    if df_plot is not None:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})
        fig.patch.set_facecolor('#0e1117')
        ax1.set_facecolor('#0e1117')
        ax1.plot(df_plot.index, df_plot['close'], color='#00d4ff', label='Giá')
        ax1.plot(df_plot.index, df_plot['alpha_trend'], color='#ffd700', label='Alpha Trend')
        ax1.legend()
        ax2.set_facecolor('#0e1117')
        ax2.plot(df_plot.index, df_plot['adx'], color='#e67e22', label='ADX')
        ax2.plot(df_plot.index, df_plot['mfi'], color='#9b59b6', label='MFI')
        ax2.axhline(20, color='red', linestyle='--', alpha=0.3)
        ax2.legend()
        st.pyplot(fig)