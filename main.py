import ccxt
import pandas as pd
import time

# Binance API 設定
api_key = '你的API_KEY'
api_secret = '你的API_SECRET'

# 初始化 Binance 交易所
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
})

# 交易參數設定
symbol = 'BTC/USDT'  # 交易對
timeframe = '1h'     # 時間週期 (1小時)
ma_period = 20       # 移動平均線週期
stoch_period = 14    # 隨機指標週期
amount = 0.001       # 每次交易數量

def get_historical_data(symbol, timeframe, limit=100):
    """獲取歷史K線數據"""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_ma(df, period):
    """計算移動平均線"""
    df['ma'] = df['close'].rolling(window=period).mean()
    return df

def calculate_stochastic(df, period):
    """計算隨機指標 (K線和D線)"""
    low_min = df['low'].rolling(window=period).min()
    high_max = df['high'].rolling(window=period).max()
    df['%K'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
    df['%D'] = df['%K'].rolling(window=3).mean()  # D線是K線的3期平均
    return df

def get_current_price(symbol):
    """獲取當前價格"""
    ticker = exchange.fetch_ticker(symbol)
    return ticker['last']

def place_order(symbol, side, amount):
    """下單"""
    try:
        order = exchange.create_order(symbol, 'market', side, amount)
        print(f"訂單成功: {side} {amount} {symbol}")
        return order
    except Exception as e:
        print(f"下單失敗: {e}")
        return None

def check_condition():
    """檢查交易條件"""
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

    # 死亡交叉 (K線下穿D線) 且現價低於均線 -> 買入
    if prev_k > prev_d and k_line < d_line and current_price < ma:
        print("條件觸發: 死亡交叉且現價低於均線，執行買入")
        place_order(symbol, 'buy', amount)

    # 黃金交叉 (K線上穿D線) 且現價高於均線 -> 賣出
    elif prev_k < prev_d and k_line > d_line and current_price > ma:
        print("條件觸發: 黃金交叉且現價高於均線，執行賣出")
        place_order(symbol, 'sell', amount)

def main():
    """主程式"""
    while True:
        try:
            check_condition()
            time.sleep(60)  # 每60秒檢查一次
        except Exception as e:
            print(f"程式錯誤: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
