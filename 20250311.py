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

# 網格交易參數
grid_levels = 5  # 網格數量
grid_upper_limit = 50000  # 網格上限價格
grid_lower_limit = 30000  # 網格下限價格
grid_prices = []  # 網格價格列表
grid_positions = {}  # 網格持倉狀態

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
    global api_key, api_secret, exchange, symbol, initial_capital, current_capital, last_backtest_time, grid_prices

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

    # 初始化網格價格
    grid_prices = generate_grid_prices(grid_lower_limit, grid_upper_limit, grid_levels)
    log_text.insert(tk.END, f"網格價格: {grid_prices}\n")

    # 啟動交易邏輯
    log_text.insert(tk.END, f"交易程式已啟動，交易對: {symbol}，初始交易成本: {initial_capital} USDT...\n")
    root.after(1000, check_condition)  # 1秒後開始檢查條件

# 生成網格價格
def generate_grid_prices(lower, upper, levels):
    step = (upper - lower) / (levels - 1)
    return [lower + i * step for i in range(levels)]

# 獲取歷史數據
def get_historical_data(symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

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

# 網格交易邏輯
def grid_trading(current_price):
    global grid_positions

    for i, price in enumerate(grid_prices):
        if current_price <= price and i not in grid_positions:
            # 買入
            amount = current_capital / current_price / grid_levels  # 每個網格的交易金額
            place_order(symbol, 'buy', amount)
            grid_positions[i] = True  # 標記該網格已買入
            log_text.insert(tk.END, f"網格 {i} 買入 @ {current_price}\n")
        elif current_price >= price and i in grid_positions:
            # 賣出
            amount = current_capital / current_price / grid_levels  # 每個網格的交易金額
            place_order(symbol, 'sell', amount)
            del grid_positions[i]  # 移除該網格的持倉
            log_text.insert(tk.END, f"網格 {i} 賣出 @ {current_price}\n")

# 回測函數
def backtest():
    global grid_levels, grid_upper_limit, grid_lower_limit, grid_prices

    log_text.insert(tk.END, "開始回測...\n")
    df = get_historical_data(symbol, timeframe, limit=168)  # 獲取過去一週的數據 (1小時週期，7天 * 24小時)

    # 模擬網格交易
    profit = 0
    positions = {}  # 網格持倉狀態
    for i in range(len(df)):
        current_price = df['close'].iloc[i]
        for j, price in enumerate(grid_prices):
            if current_price <= price and j not in positions:
                # 買入
                profit -= current_price
                positions[j] = True
            elif current_price >= price and j in positions:
                # 賣出
                profit += current_price
                del positions[j]

    log_text.insert(tk.END, f"回測結果: 總盈利 = ${profit:.2f}\n")

    # 如果績效變差，調整網格參數
    if profit < total_profit:
        log_text.insert(tk.END, "績效變差，開始調整網格參數...\n")
        grid_levels = min(10, grid_levels + 1)  # 增加網格數量
        grid_upper_limit *= 1.05  # 提高網格上限
        grid_lower_limit *= 0.95  # 降低網格下限
        grid_prices = generate_grid_prices(grid_lower_limit, grid_upper_limit, grid_levels)
        log_text.insert(tk.END, f"新網格參數: 數量 = {grid_levels}, 上限 = {grid_upper_limit}, 下限 = {grid_lower_limit}\n")

# 檢查交易條件
def check_condition():
    global current_capital, last_backtest_time

    # 每週執行一次回測
    if (datetime.now() - last_backtest_time).total_seconds() >= backtest_interval:
        backtest()
        last_backtest_time = datetime.now()

    # 獲取當前價格
    current_price = get_current_price(symbol)

    # 執行網格交易
    grid_trading(current_price)

    # 每60秒檢查一次條件
    root.after(60000, check_condition)

# 主程式
if __name__ == "__main__":
    create_ui()
