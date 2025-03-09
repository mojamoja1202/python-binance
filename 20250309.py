import ccxt
import pandas as pd
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

# 全局變數
api_key = ""
api_secret = ""
total_profit = 0  # 總盈利
exchange = None
symbol = "BTC/USDT"  # 預設交易對
initial_capital = 0  # 初始交易成本
current_capital = 0  # 當前可交易金額

# 交易參數設定
timeframe = '1h'     # 時間週期 (1小時)
ma_period = 20       # 移動平均線週期
stoch_period = 14    # 隨機指標週期

# UI介面
def create_ui():
    global api_key_entry, api_secret_entry, log_text, profit_label, symbol_combobox, capital_entry

    root = tk.Tk()
    root.title("Binance 自動交易程式")

    # API Key 輸入框
    tk.Label(root, text="API Key:").grid(row=0, column=0, padx=10, pady=10)
    api_key_entry = tk.Entry(root, width=50)
    api_key_entry.grid(row=0, column=1, padx=10, pady=10)

    # API Secret 輸入框
    tk.Label(root, text="API Secret:").grid(row=1, column=0, padx=10, pady=10)
    api_secret_entry = tk.Entry(root, width=50)
    api_secret_entry.grid(row=1, column=1, padx=10, pady=10)

    # 初始交易成本輸入框
    tk.Label(root, text="初始交易成本 (USDT):").grid(row=2, column=0, padx=10, pady=10)
    capital_entry = tk.Entry(root, width=50)
    capital_entry.grid(row=2, column=1, padx=10, pady=10)

    # 選擇交易對
    tk.Label(root, text="選擇交易對:").grid(row=3, column=0, padx=10, pady=10)
    symbol_combobox = ttk.Combobox(root, values=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"], width=47)
    symbol_combobox.set("BTC/USDT")  # 預設值
    symbol_combobox.grid(row=3, column=1, padx=10, pady=10)

    # 開始按鈕
    start_button = tk.Button(root, text="開始交易", command=start_trading)
    start_button.grid(row=4, column=0, columnspan=2, pady=10)

    # 盈利顯示
    profit_label = tk.Label(root, text="總盈利: $0", font=("Arial", 16))
    profit_label.grid(row=5, column=0, columnspan=2, pady=10)

    # 交易歷史記錄
    tk.Label(root, text="交易歷史:").grid(row=6, column=0, padx=10, pady=10)
    log_text = scrolledtext.ScrolledText(root, width=70, height=20)
    log_text.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

    root.mainloop()

# 開始交易
def start_trading():
    global api_key, api_secret, exchange, symbol, initial_capital, current_capital

    api_key = api_key_entry.get()
    api_secret = api_secret_entry.get()
    symbol = symbol_combobox.get()  # 取得使用者選擇的交易對
    initial_capital = float(capital_entry.get())  # 取得使用者輸入的初始交易成本
    current_capital = initial_capital  # 初始化當前可交易金額

    if not api_key or not api_secret or not initial_capital:
        messagebox.showerror("錯誤", "請輸入API Key、API Secret和初始交易成本！")
        return

    # 初始化 Binance 交易所
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })

    # 啟動交易邏輯
    log_text.insert(tk.END, f"交易程式已啟動，交易對: {symbol}，初始交易成本: {initial_capital} USDT...\n")
    root.after(1000, check_condition)  # 1秒後開始檢查條件

# 獲取歷史數據
def get_historical_data(symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# 計算移動平均線
def calculate_ma(df, period):
    df['ma'] = df['close'].rolling(window=period).mean()
    return df

# 計算隨機指標
def calculate_stochastic(df, period):
    low_min = df['low'].rolling(window=period).min()
    high_max = df['high'].rolling(window=period).max()
    df['%K'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
    df['%D'] = df['%K'].rolling(window=3).mean()
    return df

# 獲取當前價格
def get_current_price(symbol):
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

# 下單
def place_order(symbol, side, amount):
    global total_profit, current_capital

    try:
        order = exchange.create_order(symbol, 'market', side, amount)
        price = float(order['fills'][0]['price'])
        cost = price * amount if side == 'buy' else -price * amount
        total_profit += cost
        current_capital += cost  # 更新當前可交易金額

        profit_label.config(text=f"總盈利: ${total_profit:.2f}")
        log_text.insert(tk.END, f"訂單成功: {side} {amount} {symbol} @ {price}\n")
        log_text.see(tk.END)  # 自動滾動到最新訊息
        return order
    except Exception as e:
        log_text.insert(tk.END, f"下單失敗: {e}\n")
        log_text.see(tk.END)
        return None

# 檢查交易條件
def check_condition():
    global current_capital

    df = get_historical_data(symbol, timeframe)
    df = calculate_ma(df, ma_period)
    df = calculate_stochastic(df, stoch_period)
    
    current_price = get_current_price(symbol)
    ma = df['ma'].iloc[-1]  # 最新的移動平均線值
    k_line = df['%K'].iloc[-1]  # 最新的K線值
    d_line = df['%D'].iloc[-1]  # 最新的D線值
    prev_k = df['%K'].iloc[-2]  # 前一次的K線值
    prev_d = df['%D'].iloc[-2]  # 前一次的D線值

    print(f"當前價格: {current_price}, 移動平均線: {ma}, K線: {k_line}, D線: {d_line}")

    # 計算可交易數量
    amount = current_capital / current_price  # 根據當前可交易金額計算數量

    # 死亡交叉 (K線下穿D線) 且現價低於均線 -> 買入
    if prev_k > prev_d and k_line < d_line and current_price < ma:
        log_text.insert(tk.END, "條件觸發: 死亡交叉且現價低於均線，執行買入\n")
        place_order(symbol, 'buy', amount)

    # 黃金交叉 (K線上穿D線) 且現價高於均線 -> 檢查是否賺錢才賣出
    elif prev_k < prev_d and k_line > d_line and current_price > ma:
        # 檢查是否賺錢
        if total_profit > 0:  # 只有賺錢時才賣出
            log_text.insert(tk.END, "條件觸發: 黃金交叉且現價高於均線，執行賣出\n")
            place_order(symbol, 'sell', amount)
        else:
            log_text.insert(tk.END, "條件觸發: 黃金交叉且現價高於均線，但未賺錢，不執行賣出\n")

    # 每60秒檢查一次條件
    root.after(60000, check_condition)

# 主程式
if __name__ == "__main__":
    create_ui()
