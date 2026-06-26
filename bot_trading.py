import requests
import json
import os
from datetime import datetime

# CONFIGURACIÓN
SYMBOL = "BTCUSDT"
MAX_TRADE_USD = 100.0
STOP_LOSS_PCT = 2.0
TAKE_PROFIT_PCT = 4.0
RSI_BUY = 30
RSI_SELL = 70
BOT_FILE = "bot_data.json"

def load_json():
    if os.path.exists(BOT_FILE):
        with open(BOT_FILE, 'r') as f:
            return json.load(f)
    return {"balance": 10000.0, "holdings": 0, "avg_price": 0, "trades": []}

def save_json(data):
    with open(BOT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_price():
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
        response = requests.get(url, timeout=10)
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"Error precio: {e}")
        return None

def get_klines():
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval=5m&limit=100"
        response = requests.get(url, timeout=10)
        data = response.json()
        closes = [float(d[4]) for d in data]
        return closes
    except Exception as e:
        print(f"Error klines: {e}")
        return None

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period if period > 0 else 0
    avg_loss = sum(losses) / period if period > 0 else 0
    if avg_loss == 0:
        return 100 if avg_gain > 0 else 50
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyze(price, closes):
    rsi = calculate_rsi(closes)
    if rsi < RSI_BUY:
        return "BUY", f"RSI={rsi:.1f} (oversold)"
    elif rsi > RSI_SELL:
        return "SELL", f"RSI={rsi:.1f} (overbought)"
    else:
        return "HOLD", f"RSI={rsi:.1f} (neutral)"

def run_bot():
    print(f"\n{'='*50}")
    print(f"[{datetime.now()}] Starting bot...")
    
    price = get_price()
    closes = get_klines()
    
    if price is None or closes is None:
        print("❌ Error getting data from Binance")
        return
    
    bot = load_json()
    action, reason = analyze(price, closes)
    
    print(f"💰 BTC Price: ${price:,.2f}")
    print(f"📊 Signal: {action} - {reason}")
    print(f"💵 Balance: ${bot['balance']:,.2f}")
    print(f"📦 Holdings: {bot['holdings']:.6f} BTC")
    
    if bot['holdings'] > 0 and bot['avg_price'] > 0:
        pnl_pct = ((price - bot['avg_price']) / bot['avg_price']) * 100
        print(f"📈 PnL: {pnl_pct:+.2f}%")
        
        if pnl_pct <= -STOP_LOSS_PCT:
            print(f"🚨 STOP LOSS triggered!")
            action = "SELL"
            reason = "Stop Loss"
        elif pnl_pct >= TAKE_PROFIT_PCT:
            print(f"🎯 TAKE PROFIT triggered!")
            action = "SELL"
            reason = "Take Profit"
    
    if action == "BUY" and bot['balance'] >= MAX_TRADE_USD and bot['holdings'] == 0:
        qty = MAX_TRADE_USD / price
        bot['balance'] -= MAX_TRADE_USD
        bot['holdings'] = qty
        bot['avg_price'] = price
        bot['trades'].append({
            "time": str(datetime.now()),
            "action": "BUY",
            "price": price,
            "qty": qty,
            "reason": reason
        })
        save_json(bot)
        print(f"✅ BUY: {qty:.6f} BTC @ ${price:,.2f}")
        
    elif action == "SELL" and bot['holdings'] > 0:
        total = bot['holdings'] * price
        profit = total - (bot['holdings'] * bot['avg_price'])
        bot['balance'] += total
        bot['trades'].append({
            "time": str(datetime.now()),
            "action": "SELL",
            "price": price,
            "qty": bot['holdings'],
            "profit": profit,
            "reason": reason
        })
        bot['holdings'] = 0
        bot['avg_price'] = 0
        save_json(bot)
        print(f"🔴 SELL: ${total:,.2f} (Profit: ${profit:+,.2f})")
    
    equity = bot['balance'] + (bot['holdings'] * price)
    print(f"💎 Total Equity: ${equity:,.2f}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    run_bot()
