import ccxt
import pandas as pd
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from datetime import datetime, timedelta

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
ma_short_period = 10  # 短期均線週期
ma_long_period = 30   # 長期均線週期
rsi_period = 14       # RSI 週期
rsi_overbought = 70   # RSI 超買區域
rsi_oversold = 30     # RSI 超賣區域

# 回測相關變數
last_backtest_time = None  # 上次回測時間
backtest_interval = 7 * 24 * 60 * 60  # 每週回測一次 (單位: 秒)

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
    global api_key, api_secret, exchange, symbol, initial_capital, current_capital, last_backtest_time

    api_key = api_key_entry.get()
    api_secret = api_secret_entry.get()
    symbol = symbol_combobox.get()  # 取得使用者選擇的交易對
    initial_capital = float(capital_entry.get())  # 取得使用者輸入的初始交易成本
    current_capital = initial_capital  # 初始化當前可交易金額
    last_backtest_time = datetime.now()  # 初始化上次回測時間

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
def calculate_ma(df, short_period, long_period):
    df['ma_short'] = df['close'].rolling(window=short_period).mean()
    df['ma_long'] = df['close'].rolling(window=long_period).mean()
    return df

# 計算 RSI
def calculate_rsi(df, period):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
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

# 回測函數
def backtest():
    global ma_short_period, ma_long_period, rsi_period, rsi_overbought, rsi_oversold

    log_text.insert(tk.END, "開始回測...\n")
    df = get_historical_data(symbol, timeframe, limit=168)  # 獲取過去一週的數據 (1小時週期，7天 * 24小時)

    # 計算指標
    df = calculate_ma(df, ma_short_period, ma_long_period)
    df = calculate_rsi(df, rsi_period)

    # 模擬交易
    profit = 0
    position = 0  # 0: 無持倉, 1: 持有多頭, -1: 持有空頭
    for i in range(1, len(df)):
        ma_short = df['ma_short'].iloc[i]
        ma_long = df['ma_long'].iloc[i]
        rsi = df['rsi'].iloc[i]
        price = df['close'].iloc[i]

        # 黃金交叉 (買入)
        if ma_short > ma_long and rsi < rsi_overbought and position != 1:
            if position == -1:
                profit += price  # 平空倉
            position = 1
            profit -= price  # 開多倉

        # 死亡交叉 (賣出)
        elif ma_short < ma_long and rsi > rsi_oversold and position != -1:
            if position == 1:
                profit += price  # 平多倉
            position = -1
            profit -= price  # 開空倉

    log_text.insert(tk.END, f"回測結果: 總盈利 = ${profit:.2f}\n")

    # 如果績效變差，調整參數
    if profit < total_profit:
        log_text.insert(tk.END, "績效變差，開始調整參數...\n")
        ma_short_period = max(5, ma_short_period - 1)  # 減少短期均線週期
        ma_long_period = min(50, ma_long_period + 1)   # 增加長期均線週期
        rsi_period = max(10, rsi_period - 1)          # 減少 RSI 週期
        log_text.insert(tk.END, f"新參數: MA_short = {ma_short_period}, MA_long = {ma_long_period}, RSI_period = {rsi_period}\n")

# 檢查交易條件
def check_condition():
    global current_capital, last_backtest_time

    # 每週執行一次回測
    if (datetime.now() - last_backtest_time).total_seconds() >= backtest_interval:
        backtest()
        last_backtest_time = datetime.now()

    df = get_historical_data(symbol, timeframe)
    df = calculate_ma(df, ma_short_period, ma_long_period)
    df = calculate_rsi(df, rsi_period)
    
    current_price = get_current_price(symbol)
    ma_short = df['ma_short'].iloc[-1]  # 最新的短期均線值
    ma_long = df['ma_long'].iloc[-1]    # 最新的長期均線值
    rsi = df['rsi'].iloc[-1]            # 最新的 RSI 值

    print(f"當前價格: {current_price}, 短期均線: {ma_short}, 長期均線: {ma_long}, RSI: {rsi}")

    # 計算可交易數量
    amount = current_capital / current_price  # 根據當前可交易金額計算數量

    # 黃金交叉 (短期均線上穿長期均線) 且 RSI 未超買 -> 買入
    if ma_short > ma_long and rsi < rsi_overbought:
        log_text.insert(tk.END, "條件觸發: 黃金交叉且 RSI 未超買，執行買入\n")
        place_order(symbol, 'buy', amount)

    # 死亡交叉 (短期均線下穿長期均線) 且 RSI 未超賣 -> 檢查是否賺錢才賣出
    elif ma_short < ma_long and rsi > rsi_oversold:
        if total_profit > 0:  # 只有賺錢時才賣出
            log_text.insert(tk.END, "條件觸發: 死亡交叉且 RSI 未超賣，執行賣出\n")
            place_order(symbol, 'sell', amount)
        else:
            log_text.insert(tk.END, "條件觸發: 死亡交叉且 RSI 未超賣，但未賺錢，不執行賣出\n")

    # 每60秒檢查一次條件
    root.after(60000, check_condition)

# 主程式
if __name__ == "__main__":
    create_ui()
