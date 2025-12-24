# -*- coding: utf-8 -*-
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
import threading
import warnings
import os
import time
import requests_cache 
from datetime import timedelta
from datetime import datetime
from mf_chart import MFTrendChart
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg 
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

warnings.filterwarnings("ignore")

# Cấu hình Cache: Lưu dữ liệu trong 30 phút để tránh tải lại quá nhiều
session = requests_cache.CachedSession(
    'yfinance_cache',
    expire_after=timedelta(minutes=30), # Sau 30p mới tải mới từ Yahoo
    backend='sqlite'
)

class MFTrendFinal:
    def __init__(self):
        print("--- Khởi tạo MF-TREND V7.0 - Final Edition ---")
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("MF-TREND PRO V7.0 - TIMESLEEP")
        self.root.geometry("1500x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_app_closing)
        
        self.watchlist_files = {"CÁ NHÂN": "watchlist_ca_nhan.txt", "THỊ TRƯỜNG": "watchlist_thi_truong.txt"}
        self.current_mode = "CÁ NHÂN"
        self.symbols = []
        self.full_data = {} 
        self.full_results = []
        
        self.load_symbols()
        self.setup_ui()

    def setup_ui(self):
        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self.root, width=250)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        ctk.CTkLabel(self.sidebar, text="MF-TREND SYSTEM", font=("Arial", 18, "bold")).pack(pady=10)
        self.btn_scan = ctk.CTkButton(self.sidebar, text="BẮT ĐẦU QUÉT", command=self.start_scan, fg_color="#1f538d", height=40)
        self.btn_scan.pack(pady=10, padx=10)

        # 1. Chọn danh mục (Cá nhân/Thị trường)
        ctk.CTkLabel(self.sidebar, text="CHỌN DANH MỤC", font=("Arial", 12, "bold"), text_color="#3498db").pack(pady=(10, 5))
        self.seg_watchlist = ctk.CTkSegmentedButton(self.sidebar, values=["CÁ NHÂN", "THỊ TRƯỜNG"], command=self.switch_watchlist)
        self.seg_watchlist.set("CÁ NHÂN")
        self.seg_watchlist.pack(pady=5, padx=10)

        # 2. Quản lý mã
        ctk.CTkLabel(self.sidebar, text="QUẢN LÝ MÃ CK", font=("Arial", 12, "bold"), text_color="#e67e22").pack(pady=(15, 5))
        self.entry_symbol = ctk.CTkEntry(self.sidebar, placeholder_text="Mã CK (VD: SSI)")
        self.entry_symbol.pack(pady=5, padx=10)
        
        btn_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        btn_box.pack(pady=5)
        ctk.CTkButton(btn_box, text="THÊM", command=self.add_symbol, fg_color="#27ae60", width=80).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="XÓA", command=self.remove_symbol, fg_color="#c0392b", width=80).pack(side="left", padx=5)

        self.symbol_listbox = tk.Listbox(self.sidebar, bg="#1e1e1e", fg="white", font=("Arial", 11), borderwidth=0, selectbackground="#3498db")
        self.symbol_listbox.pack(pady=10, padx=10, fill="both", expand=True)
        self.symbol_listbox.bind("<Double-1>", lambda e: self.on_watchlist_double_click(e))
        
        # 3. Bộ lọc nhanh (Quick Filter)
        ctk.CTkLabel(self.sidebar, text="BỘ LỌC NHANH", font=("Arial", 12, "bold"), text_color="#9b59b6").pack(pady=(10, 2))
        self.filter_var = ctk.StringVar(value="TẤT CẢ")
        self.filter_menu = ctk.CTkOptionMenu(self.sidebar, values=["TẤT CẢ", "CHỈ CÓ TÍN HIỆU"], variable=self.filter_var, command=lambda x: self.update_table())
        self.filter_menu.pack(pady=5, padx=10)

        self.refresh_listbox()
        self.status_label = ctk.CTkLabel(self.sidebar, text="Click đúp mã để xem Chart", text_color="gray")
        self.status_label.pack(side="bottom", pady=10)
        
        
    
        # --- MAIN BOARD ---
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Bảng Alpha Trend (Hỗ trợ Double Click)
        ctk.CTkLabel(self.main_frame, text="1. CHIẾN LƯỢC ALPHA TREND ", font=("Arial", 14, "bold"), text_color="#3498db").pack(pady=(10, 5))
        self.tree_at = self.create_tree(self.main_frame, ("Mã", "Giá", "Status", "Gap %", "SL Di Động", "Khuyến nghị Alpha"))
        self.tree_at.bind("<Double-1>", lambda e: self.on_double_click(e))

        # Bảng MF-Trend
        ctk.CTkLabel(self.main_frame, text="2. ĐỘNG LƯỢNG & TÍCH LŨY (MF-TREND)", font=("Arial", 14, "bold"), text_color="#e67e22").pack(pady=(20, 5))
        self.tree_mf = self.create_tree(self.main_frame, ("Mã", "ADX_t0", "MFI_t0", "RSI_t0", "Dòng tiền", "Tín hiệu MF"))
        self.tree_mf.bind("<Double-1>", lambda e: self.on_double_click(e))
        
        # Thêm nút Xuất Excel vào cột bên trái (dưới nút Chọn danh mục)
        self.btn_excel = ctk.CTkButton(
            self.sidebar, 
            text="XUẤT EXCEL", 
            command=self.export_to_excel,
            fg_color="#27ae60", # Màu xanh lá đậm
            hover_color="#2ecc71"
        )
        self.btn_excel.pack(pady=10, padx=20, fill="x")
    
    def export_to_excel(self):
        if not self.full_results:
            print("Chưa có dữ liệu để xuất! Hãy quét danh sách trước.")
            return
            
        try:
            # Chuyển đổi dữ liệu từ full_results sang danh sách phẳng để làm Excel
            excel_data = []
            for item in self.full_results:
                row = {
                    "Mã CK": item['s'],
                    "Giá Hiện Tại": item['p'],
                    "Trạng Thái": item['al'][0],
                    "Gap %": item['al'][1],
                    "Stoploss": item['al'][2],
                    "Khuyến Nghị": item['al'][3],
                    "ADX": item['mf'][0],
                    "MFI": item['mf'][1],
                    "RSI": item['mf'][2],
                    "Dòng Tiền": item['mf'][3],
                    "Tín Hiệu MF": item['mf'][4]
                }
                excel_data.append(row)
            
            # Tạo DataFrame và xuất file
            df_export = pd.DataFrame(excel_data)
            
            # Đặt tên file theo ngày giờ để không bị ghi đè
            filename = f"BaoCao_MFTrend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            df_export.to_excel(filename, index=False)
            
            # Thông báo cho người dùng
            print(f"--- ĐÃ XUẤT FILE: {filename} ---")
            tk.messagebox.showinfo("Thành công", f"Đã lưu báo cáo tại:\n{filename}")
            
        except Exception as e:
            print(f"Lỗi khi xuất Excel: {e}")
            tk.messagebox.showerror("Lỗi", f"Không thể xuất file: {e}")

    def create_tree(self, parent, columns):
        container = tk.Frame(parent, bg="#2b2b2b")
        container.pack(fill="x", padx=15, pady=5)
        tree = ttk.Treeview(container, columns=columns, show='headings', height=13)
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        for col in columns:
            tree.heading(col, text=col, command=lambda _col=col: self.sort_column(tree, _col, False))
            tree.column(col, width=150, anchor="center")        
        tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")
        # Định nghĩa Tag màu sắc (như trong ảnh image_ffc3e7.jpg)
        tree.tag_configure('buy_now', background='#27ae60', foreground='white')
        tree.tag_configure('hit_sl', background='#c0392b', foreground='white')
        tree.tag_configure('strong_signal', background='#2ecc71', foreground='black')
        return tree

    def switch_watchlist(self, mode):
        self.current_mode = mode
        self.load_symbols()
        self.refresh_listbox()

    def show_chart(self, s):
        if s not in self.full_data: 
            return
        # Gọi module ngoài xử lý đồ thị
        MFTrendChart.show_chart(self.root, s, self.full_data[s])

    def start_scan(self):
        self.btn_scan.configure(state="disabled", text="ĐANG QUÉT...")
        threading.Thread(target=self.run_scanner, daemon=True).start()

    def run_scanner(self):
        self.full_results = []
        total = len(self.symbols)
        
        for i, s in enumerate(self.symbols):
            try:
                self.btn_scan.configure(text=f"QUÉT: {i+1}/{total} ({s})")
                
                df = yf.download(f"{s}.VN", period="8mo", progress=False, auto_adjust=True, timeout=30)
                
                if df is None or df.empty or len(df) < 30:
                    continue
                
                # 1. Làm sạch và tính toán chỉ báo
                df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
                
                # Tính toán các chỉ báo MF-Trend
                df['mfi'] = ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=14)
                df['rsi'] = ta.rsi(df['close'], length=14)
                df['adl'] = ta.ad(df['high'], df['low'], df['close'], df['volume'])
                
                # Tính ADX và GÁN VÀO DF để MFChart có thể đọc được
                adx_df = ta.adx(df['high'], df['low'], df['close'])
                df['adx_14'] = adx_df['ADX_14'] 
                
                # Tính Stoploss và MA20 cho Chiến lược Alpha
                atr = ta.atr(df['high'], df['low'], df['close'], length=14)
                df['sl_line'] = (df['close'].shift(1) - (atr.shift(1) * 2)).rolling(window=20, min_periods=1).max()
                df['ma20'] = df['close'].rolling(window=20).mean()
                
                # Lưu toàn bộ dữ liệu (đã bao gồm cột adx_14) vào bộ nhớ
                self.full_data[s] = df 
                
                # 2. Kiểm tra điều kiện Phương án 1 (Main Buy)
                t0, t5, t20 = -1, -6, -21
                
                # Tiêu chí Xu hướng (ADX): ADXt0 > 20 và ADXt0 > ADXt5
                c_adx = (df['adx_14'].iloc[t0] > 20) and (df['adx_14'].iloc[t0] > df['adx_14'].iloc[t5])
                
                # Tiêu chí Động lượng (MFI & RSI): t0 > t20 và trong ngưỡng
                c_mfi = (48 <= df['mfi'].iloc[t0] <= 68) and (df['mfi'].iloc[t0] > df['mfi'].iloc[t20])
                c_rsi = (48 <= df['rsi'].iloc[t0] <= 58) and (df['rsi'].iloc[t0] > df['rsi'].iloc[t20])
                
                # Tiêu chí Tích lũy (ADL): t0 > t20
                c_adl = df['adl'].iloc[t0] > df['adl'].iloc[t20]
                
                # Xác định tín hiệu
                khuyen_nghi = "️🎖️ VÀO LỆNH" if (df['close'].iloc[t0] > df['sl_line'].iloc[t0] and df['close'].iloc[t0] > df['ma20'].iloc[t0]) else "❌ GÃY TREND"
                sig = "🔥 MUA CHÍNH" if (c_adx and c_mfi and c_rsi and c_adl) else "Theo dõi"
                
                self.full_results.append({
                    "s": s, "p": int(round(df['close'].iloc[t0])), 
                    "al": ("BUY" if df['close'].iloc[t0] > df['ma20'].iloc[t0] else "SELL", f"{((df['close'].iloc[t0]/df['ma20'].iloc[t0])-1)*100:.1f}%", f"{int(round(df['sl_line'].iloc[t0])):,}", khuyen_nghi),
                    "mf": (f"{df['adx_14'].iloc[t0]:.1f}", f"{df['mfi'].iloc[t0]:.1f}", f"{df['rsi'].iloc[t0]:.1f}", "Tích cực" if c_adl else "Yêu", sig)
                })
                
                if not getattr(df, 'from_cache', False): time.sleep(0.5)
                
            except Exception as e:
                print(f"Lỗi mã {s}: {e}")
                continue

        self.root.after(0, self.update_table)

    def update_table(self):
        f_mode = self.filter_var.get()
        for t in [self.tree_at, self.tree_mf]:
            for i in t.get_children(): t.delete(i)
        for r in self.full_results:
            if f_mode == "CHỈ CÓ TÍN HIỆU" and "VÀO" not in r["al"][3] and "MUA" not in r["mf"][4]: continue
            tag = 'buy_now' if "VÀO" in r["al"][3] else ('hit_sl' if "GÃY" in r["al"][3] else "")
            self.tree_at.insert("", "end", values=(r["s"], f"{r['p']:,}", *r["al"]), tags=(tag,))
            mftag = 'strong_signal' if "MUA" in r["mf"][4] else ""
            self.tree_mf.insert("", "end", values=(r["s"], *r["mf"]), tags=(mftag,))
        self.btn_scan.configure(state="normal", text="BẮT ĐẦU QUÉT")

    def on_app_closing(self):
        plt.close('all')
        self.root.destroy()
        os._exit(0) # Thoát triệt để tránh treo luồng

    # --- HỆ THỐNG WATCHLIST ---
    def load_symbols(self):
        f = self.watchlist_files[self.current_mode]
        if os.path.exists(f):
            with open(f, "r") as file: self.symbols = [l.strip().upper() for l in file if l.strip()]
        else: self.symbols = ["SSI", "HPG", "FPT"]

    def save_symbols(self):
        f = self.watchlist_files[self.current_mode]
        with open(f, "w") as file:
            for s in self.symbols: file.write(s + "\n")

    def add_symbol(self):
        s = self.entry_symbol.get().upper().strip()
        if s and s not in self.symbols:
            self.symbols.append(s); self.save_symbols(); self.refresh_listbox(); self.entry_symbol.delete(0, tk.END)

    def remove_symbol(self):
        sel = self.symbol_listbox.curselection()
        if sel:
            s = self.symbol_listbox.get(sel[0])
            self.symbols.remove(s); self.save_symbols(); self.refresh_listbox()

    def refresh_listbox(self):
        self.symbol_listbox.delete(0, tk.END)
        for s in self.symbols: self.symbol_listbox.insert(tk.END, s)

    def on_double_click(self, event):
        item = event.widget.identify_row(event.y)
        if item:
            val = event.widget.item(item, "values")
            if val: self.show_chart(val[0])

    def on_watchlist_double_click(self, event):
        sel = self.symbol_listbox.curselection()
        if sel:
            s = self.symbol_listbox.get(sel[0])
            if s in self.full_data: self.show_chart(s)

    def sort_column(self, tree, col, reverse):
        data = []
        for k in tree.get_children(''):
            val = str(tree.set(k, col))
            # Gỡ bỏ ký tự đặc biệt để so sánh số
            clean = val.replace(',', '').replace('%', '').replace('🔥', '').replace('️🎖️', '').replace('❌', '').strip()
            try: sort_val = float(clean)
            except: sort_val = val.lower()
            data.append((sort_val, k))
        data.sort(reverse=reverse)
        for i, (v, k) in enumerate(data): tree.move(k, '', i)
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))

if __name__ == "__main__":
    app = MFTrendFinal()
    app.root.mainloop()