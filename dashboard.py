import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objects as go
import time

# ============================================
# CONFIGURACIÓN DE PÁGINA
# ============================================
st.set_page_config(
    page_title="🤖 Crypto Bot Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .metric-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    .buy-signal { color: #3fb950; font-weight: bold; }
    .sell-signal { color: #f85149; font-weight: bold; }
    .hold-signal { color: #8b949e; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Crypto Bot Pro - Dashboard Multi-Mercado")

# ============================================
# LISTA DE CRIPTOMONEDAS
# ============================================
CRYPTOS = {
    "Bitcoin": {"symbol": "BTCUSDT", "name": "BTC"},
    "Ethereum": {"symbol": "ETHUSDT", "name": "ETH"},
    "Solana": {"symbol": "SOLUSDT", "name": "SOL"},
    "BNB": {"symbol": "BNBUSDT", "name": "BNB"},
    "Cardano": {"symbol": "ADAUSDT", "name": "ADA"},
    "Ripple": {"symbol": "XRPUSDT", "name": "XRP"}
}

# ============================================
# FUNCIONES
# ============================================
@st.cache_data(ttl=60)
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        data = requests.get(url, timeout=5).json()
        return float(data['price'])
    except:
        return None

@st.cache_data(ttl=60)
def get_klines(symbol, interval='1h', limit=100):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = requests.get(url, timeout=5).json()
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qv', 't', 'tb', 'tq', 'ig'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except:
        return None

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    deltas = closes.diff()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def analyze_market(df):
    if df is None or len(df) < 30:
        return "HOLD", 50, []
    
    closes = df['close']
    rsi = calculate_rsi(closes)
    
    # MACD
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    
    # Bollinger
    sma20 = closes.rolling(20).mean()
    std20 = closes.rolling(20).std()
    bb_upper = sma20 + (std20 * 2)
    bb_lower = sma20 - (std20 * 2)
    
    current_price = closes.iloc[-1]
    
    buy_score = 0
    sell_score = 0
    reasons = []
    
    # RSI
    if rsi < 30:
        buy_score += 1
        reasons.append(f"✅ RSI sobreventa ({rsi:.1f})")
    elif rsi > 70:
        sell_score += 1
        reasons.append(f"❌ RSI sobrecompra ({rsi:.1f})")
    
    # MACD
    if macd.iloc[-1] > signal.iloc[-1]:
        buy_score += 1
        reasons.append("✅ MACD alcista")
    else:
        sell_score += 1
        reasons.append("❌ MACD bajista")
    
    # Bollinger
    if current_price <= bb_lower.iloc[-1]:
        buy_score += 1
        reasons.append("✅ Precio en banda inferior")
    elif current_price >= bb_upper.iloc[-1]:
        sell_score += 1
        reasons.append("❌ Precio en banda superior")
    
    if buy_score >= 2:
        return "BUY", rsi, reasons
    elif sell_score >= 2:
        return "SELL", rsi, reasons
    else:
        return "HOLD", rsi, reasons

def load_bot_data(crypto_name):
    """Carga los datos del bot desde GitHub"""
    try:
        url = f"https://raw.githubusercontent.com/chitomax/criptobot/main/bot_data.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"balance": 10000.0, "holdings": 0, "avg_price": 0, "trades": []}

# ============================================
# BARRA LATERAL
# ============================================
st.sidebar.header("⚙️ Configuración")
selected_crypto = st.sidebar.selectbox("Seleccionar Criptomoneda", list(CRYPTOS.keys()))
show_chart = st.sidebar.checkbox("Mostrar Gráficos", value=True)
auto_refresh = st.sidebar.checkbox("Auto-Refresco (30s)", value=False)

# ============================================
# ANÁLISIS PRINCIPAL
# ============================================
crypto_info = CRYPTOS[selected_crypto]
symbol = crypto_info['symbol']
name = crypto_info['name']

st.header(f"📊 {selected_crypto} ({symbol})")

# Obtener datos
price = get_price(symbol)
df = get_klines(symbol, '1h', 100)
action, rsi, reasons = analyze_market(df)

# Métricas principales
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💰 Precio Actual", f"${price:,.2f}" if price else "N/A")

with col2:
    rsi_color = "🟢" if rsi < 30 else "🔴" if rsi > 70 else "⚪"
    st.metric("📊 RSI", f"{rsi:.1f}")

with col3:
    if action == "BUY":
        st.markdown(f"### 🟢 SEÑAL: COMPRA")
    elif action == "SELL":
        st.markdown(f"### 🔴 SEÑAL: VENTA")
    else:
        st.markdown(f"### ⚪ SEÑAL: ESPERAR")

with col4:
    bot_data = load_bot_data(selected_crypto)
    st.metric("💵 Balance Bot", f"${bot_data['balance']:,.2f}")

# Razones del análisis
st.markdown("### 📋 Análisis Técnico")
for reason in reasons:
    st.write(reason)

# ============================================
# GRÁFICO
# ============================================
if show_chart and df is not None:
    st.markdown("---")
    st.subheader(f"📈 Gráfico de {selected_crypto}")
    
    fig = go.Figure()
    
    # Precio
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['close'],
        mode='lines',
        name='Precio',
        line=dict(color='#F7931A' if name == 'BTC' else '#627EEA', width=2)
    ))
    
    # Bandas de Bollinger
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    bb_upper = sma20 + (std20 * 2)
    bb_lower = sma20 - (std20 * 2)
    
    fig.add_trace(go.Scatter(x=df['time'], y=bb_upper, mode='lines', 
                            name='BB Superior', line=dict(color='gray', dash='dash'), opacity=0.5))
    fig.add_trace(go.Scatter(x=df['time'], y=bb_lower, mode='lines', 
                            name='BB Inferior', line=dict(color='gray', dash='dash'), opacity=0.5,
                            fill='tonexty'))
    
    fig.update_layout(
        title=f"{selected_crypto} - Precio y Bandas de Bollinger",
        xaxis_title="Tiempo",
        yaxis_title="Precio (USDT)",
        template="plotly_dark",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# HISTORIAL DE OPERACIONES
# ============================================
st.markdown("---")
st.subheader(f"📋 Historial de Operaciones - {selected_crypto}")

if bot_data['trades']:
    df_trades = pd.DataFrame(bot_data['trades'])
    
    # Formatear tabla
    df_trades['Hora'] = pd.to_datetime(df_trades['time']).dt.strftime('%Y-%m-%d %H:%M')
    df_trades['Acción'] = df_trades['action'].apply(lambda x: '🟢 COMPRA' if x == 'BUY' else '🔴 VENTA')
    df_trades['Precio'] = df_trades['price'].apply(lambda x: f"${x:,.2f}")
    df_trades['Cantidad'] = df_trades['qty'].apply(lambda x: f"{x:.6f}")
    
    if 'profit' in df_trades.columns:
        df_trades['Ganancia'] = df_trades['profit'].apply(lambda x: f"${x:+,.2f}")
        st.dataframe(df_trades[['Hora', 'Acción', 'Precio', 'Cantidad', 'Ganancia', 'reason']].tail(10), use_container_width=True)
    else:
        st.dataframe(df_trades[['Hora', 'Acción', 'Precio', 'Cantidad', 'reason']].tail(10), use_container_width=True)
else:
    st.info("📝 Sin operaciones registradas aún")

# ============================================
# VISTA GENERAL DE TODAS LAS CRYPTOS
# ============================================
st.markdown("---")
st.subheader("🌍 Vista General de Todos los Mercados")

cols = st.columns(3)
for idx, (crypto_name, crypto_info) in enumerate(CRYPTOS.items()):
    col = cols[idx % 3]
    
    price = get_price(crypto_info['symbol'])
    df = get_klines(crypto_info['symbol'], '1h', 100)
    action, rsi, _ = analyze_market(df)
    
    with col:
        st.markdown(f"### {crypto_name}")
        st.write(f"**Precio:** ${price:,.2f}" if price else "**Precio:** N/A")
        st.write(f"**RSI:** {rsi:.1f}")
        
        if action == "BUY":
            st.markdown("<p class='buy-signal'>🟢 COMPRA</p>", unsafe_allow_html=True)
        elif action == "SELL":
            st.markdown("<p class='sell-signal'>🔴 VENTA</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p class='hold-signal'>⚪ ESPERAR</p>", unsafe_allow_html=True)
        
        st.markdown("---")

# ============================================
# AUTO-REFRESCO
# ============================================
if auto_refresh:
    time.sleep(30)
    st.rerun()

# Footer
st.caption(f"🔄 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
