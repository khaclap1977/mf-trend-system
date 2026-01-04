import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime

# --- ĐỌC DỮ LIỆU TỐI ƯU TỪ FILE GOLD.XLSX ---
def load_gold_settings():
    try:
        # Đọc file GOLD.xlsx được upload trên GitHub
        df_gold = pd.read_excel("GOLD.xlsx") 
        # Chuyển thành dictionary để tra cứu nhanh theo Mã (Symbol)
        return df_gold.set_index('Symbol').to_dict('index')
    except:
        st.error("Không tìm thấy file GOLD.xlsx trên GitHub!")
        return {}

def scan_with_tolerance(s, df, gold_settings):
    """Quét dựa trên tham số tối ưu và Tolerance từ file GOLD"""
    t0, t5, t20 = -1, -6, -21
    
    # Lấy thông số tối ưu riêng cho mã s, nếu không có thì dùng mặc định
    opt = gold_settings.get(s, {
        'ADX_Min': 20, 
        'RSI_Buy': 48, 
        'MFI_Buy': 48, 
        'Tolerance': 0.02 # Ngưỡng sai số mặc định 2%
    })
    
    tolerance = opt.get('Tolerance', 0.02)
    
    # 1. Điều kiện ADX Tối ưu: t0 > ADX_Min (từ file GOLD) và đang tăng
    c_adx = (df['adx'].iloc[t0] >= opt['ADX_Min'] * (1 - tolerance)) and (df['adx'].iloc[t0] > df['adx'].iloc[t5])
    
    # 2. Điều kiện MFI/RSI Tối ưu (Dùng ngưỡng từ file GOLD thay vì 48-68)
    c_mfi = (df['mfi'].iloc[t0] >= opt['MFI_Buy'] * (1 - tolerance)) and (df['mfi'].iloc[t0] > df['mfi'].iloc[t20])
    c_rsi = (df['rsi'].iloc[t0] >= opt['RSI_Buy'] * (1 - tolerance)) and (df['rsi'].iloc[t0] > df['rsi'].iloc[t20])
    
    # 3. Điều kiện Alpha (Giá nằm trên Alpha Trend từ file MFTrend.py)
    c_alpha = df['close'].iloc[t0] > df['alpha_trend'].iloc[t0]
    
    # ĐIỂM VÀNG HỘI TỤ
    is_gold = c_adx and c_mfi and c_rsi and c_alpha
    
    return {
        "Mã": s,
        "ADX Hiện tại": f"{df['adx'].iloc[t0]:.1f}",
        "ADX Mục tiêu": opt['ADX_Min'],
        "Tín hiệu": "🔥 ĐIỂM VÀNG" if is_gold else "Đang tích lũy",
        "Chiến thuật": "MUA 1/3 (P1)" if is_gold else "Quan sát" [cite: 2025-12-09]
    }

# --- GIAO DIỆN APP ---
st.title("🌟 MF-TREND GOLD OPTIMIZER")

gold_params = load_gold_settings()

if st.button("🚀 QUÉT THEO ĐIỂM TỐI ƯU"):
    results = []
    # Chỉ quét các mã có trong file GOLD.xlsx để đảm bảo tính chính xác
    symbols = list(gold_params.keys())
    
    for s in symbols:
        # Giả định hàm process_data đã tính toán ADX, MFI, RSI, AlphaTrend
        data = process_data(s) 
        if data is not None:
            results.append(scan_with_tolerance(s, data, gold_params))
            
    st.table(pd.DataFrame(results))