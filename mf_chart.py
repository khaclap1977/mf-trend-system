import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import customtkinter as ctk

class MFTrendChart:
    @staticmethod
    def show_chart(parent_root, symbol, df):
        if df is None or df.empty:
            return
        
        # Tạo cửa sổ hiển thị
        chart_window = ctk.CTkToplevel(parent_root)
        chart_window.title(f"MF-Trend Pro Analysis: {symbol}")
        chart_window.geometry("1400x950")
        chart_window.configure(fg_color="#121212")

        # Frame chứa Toolbar (ẩn đi nếu muốn giao diện tối giản)
        toolbar_frame = ctk.CTkFrame(chart_window, height=45, fg_color="#1e1e1e")
        toolbar_frame.pack(side="bottom", fill="x")

        # Khởi tạo đồ thị đa tầng
        fig = plt.figure(figsize=(14, 8), dpi=100)
        fig.patch.set_facecolor('#121212') 
        gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.15)
        
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        ax4 = fig.add_subplot(gs[3], sharex=ax1)

        # Lấy các giá trị cuối cùng cho Legend [cite: 2025-11-22]
        last_price = df['close'].iloc[-1]
        last_ma20 = df['ma20'].iloc[-1]
        last_sl = df['sl_line'].iloc[-1]
        last_mfi = df['mfi'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        last_adx = df['adx_14'].iloc[-1]
        last_adl = df['adl'].iloc[-1]

        # --- LOGIC TÍNH TÍN HIỆU HỘI TỤ (P1) CHUẨN MF-TREND --- [cite: 2025-12-09]
        cond_adx = (df['adx_14'] > 20) & (df['adx_14'] > df['adx_14'].shift(5)) # [cite: 2025-12-08]
        cond_mfi = (df['mfi'] >= 48) & (df['mfi'] <= 68) & (df['mfi'] > df['mfi'].shift(20))
        cond_rsi = (df['rsi'] >= 48) & (df['rsi'] <= 58) & (df['rsi'] > df['rsi'].shift(20))
        cond_adl = (df['adl'] > df['adl'].shift(20))
        cond_price = (df['close'] > df['ma20']) & (df['close'] > df['sl_line'])
        
        buy_signals = df[cond_adx & cond_mfi & cond_rsi & cond_adl & cond_price]

        # --- VẼ CÁC TẦNG DỮ LIỆU ---
        # Tầng 1: Giá & Stoploss
        ax1.plot(df.index, df['close'], label=f'Giá: {last_price:,.0f}', color='#00d4ff', linewidth=1.5)
        ax1.plot(df.index, df['ma20'], label=f'MA20: {last_ma20:,.0f}', color='#ffcc00', linestyle='--')
        ax1.plot(df.index, df['sl_line'], label=f'Stoploss: {last_sl:,.0f}', color='#e74c3c', linestyle=':', alpha=0.8)
        if not buy_signals.empty:
            ax1.scatter(buy_signals.index, buy_signals['close'] * 0.98, marker='^', color='#2ecc71', s=120, label='ĐIỂM HỘI TỤ (P1)', zorder=5)

        # Tầng 2: MFI & RSI [cite: 2025-12-02]
        ax2.plot(df.index, df['mfi'], label=f'MFI: {last_mfi:.1f}', color='#9b59b6')
        ax2.plot(df.index, df['rsi'], label=f'RSI: {last_rsi:.1f}', color='#f1c40f')
        ax2.axhspan(48, 68, color='#2ecc71', alpha=0.1, label='MF-Zone')

        # Tầng 3: ADX [cite: 2025-12-08]
        ax3.plot(df.index, df['adx_14'], label=f'ADX: {last_adx:.1f}', color='#e67e22')
        ax3.axhline(y=20, color='#2ecc71', linestyle='-', alpha=0.5)

        # Tầng 4: ADL [cite: 2025-11-22]
        adl_text = f"{last_adl/1e9:.2f} Tỷ" if abs(last_adl) >= 1e9 else f"{last_adl/1e6:.2f} Tr"
        ax4.plot(df.index, df['adl'], label=f'ADL: {adl_text}', color='#1abc9c')

        # Định dạng thẩm mỹ [cite: 2025-12-20]
        for ax in [ax1, ax2, ax3, ax4]:
            ax.set_facecolor('#121212')
            ax.tick_params(colors='white', labelsize=9)
            ax.grid(True, color='gray', alpha=0.05)
            ax.yaxis.tick_right()
            ax.legend(loc='upper left', fontsize=9, facecolor='black', labelcolor='white', framealpha=0.7)
            if ax != ax4: plt.setp(ax.get_xticklabels(), visible=False)

        fig.subplots_adjust(left=0.05, right=0.94, top=0.96, bottom=0.06)

        canvas = FigureCanvasTkAgg(fig, master=chart_window)
        canvas.draw()
        
        # Khởi tạo Toolbar nhưng không kích hoạt Pan mặc định
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()

        # --- LOGIC TƯƠNG TÁC CHUỘT THÔNG MINH ---
        class UnifiedInteraction:
            def __init__(self):
                self.press = None

            def on_press(self, event):
                if event.inaxes != ax1 or event.button != 1: return
                self.press = event.xdata, ax1.get_xlim()

            def on_motion(self, event):
                if self.press is None or event.inaxes != ax1 or event.xdata is None: return
                xpress, xlim = self.press
                dx = event.xdata - xpress
                ax1.set_xlim(xlim[0] - dx, xlim[1] - dx)
                canvas.draw_idle()

            def on_release(self, event):
                self.press = None

            def on_scroll(self, event):
                if event.inaxes is None: return
                base_scale = 1.2
                cur_xlim = ax1.get_xlim()
                scale_factor = 1/base_scale if event.button == 'up' else base_scale
                new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
                relx = (cur_xlim[1] - event.xdata) / (cur_xlim[1] - cur_xlim[0])
                ax1.set_xlim([event.xdata - new_width * (1 - relx), event.xdata + new_width * relx])
                canvas.draw_idle()

        ui = UnifiedInteraction()
        fig.canvas.mpl_connect('button_press_event', ui.on_press)
        fig.canvas.mpl_connect('motion_notify_event', ui.on_motion)
        fig.canvas.mpl_connect('button_release_event', ui.on_release)
        fig.canvas.mpl_connect('scroll_event', ui.on_scroll)

        canvas.get_tk_widget().pack(fill="both", expand=True)