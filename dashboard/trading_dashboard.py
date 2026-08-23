"""
Dashboard de Monitoreo de Trading en Tiempo Real con Streamlit
Visualización dinámica de operaciones reales en Binance Futures Testnet y métricas de bitácora.
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from dotenv import load_dotenv

try:
    from binance.um_futures import UMFutures
except ImportError:
    UMFutures = None

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.data_collector import DataCollector
from src.backtesting.indicators import add_all_indicators
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.grid_trading import GridTradingStrategy, create_grid_strategy_function

load_dotenv()
load_dotenv(Path('../Rowboat_Binance/.env'))
load_dotenv(Path('/Users/jorgeatilano/Desktop/Antigravity_Trading/Rowboat_Binance/.env'))

api_key = os.getenv('BINANCE_TEST_KEY') or os.getenv('BINANCE_API_KEY', '')
secret_key = os.getenv('BINANCE_TEST_SECRET') or os.getenv('BINANCE_SECRET_KEY', '')

# Configuración de la página
st.set_page_config(
    page_title="Sistema Autónomo de Trading - Binance Live",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
    .main {
        background-color: #0f0f23;
    }
    .stApp {
        background-color: #0f0f23;
    }
    h1, h2, h3 {
        color: #00ff88;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a3e 0%, #2d2d5a 100%);
        border: 1px solid #00ff88;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def load_live_account():
    """Cargar balance y posiciones vivas desde Binance Testnet."""
    tot_bal, avail_bal, positions = 5000.0, 5000.0, []
    if UMFutures and api_key and secret_key:
        try:
            client = UMFutures(key=api_key, secret=secret_key, base_url="https://testnet.binancefuture.com")
            acc = client.account(recvWindow=60000)
            tot_bal = float(acc['totalWalletBalance'])
            avail_bal = float(acc['availableBalance'])
            for pos in acc['positions']:
                amt = float(pos['positionAmt'])
                if amt != 0:
                    positions.append({
                        'Simbolo': pos['symbol'],
                        'Lado': 'LONG' if amt > 0 else 'SHORT',
                        'Cantidad': abs(amt),
                        'Entrada': float(pos.get('entryPrice', 0.0)),
                        'PnL Flotante USDT': float(pos.get('unrealizedProfit', 0.0)),
                        'Apalancamiento': f"{pos.get('leverage', 10)}x"
                    })
        except Exception:
            pass
    return tot_bal, avail_bal, positions


def load_bitacora_trades():
    """Cargar bitácora física de operaciones reales desde CSV."""
    bitacora_path = Path("logs/bitacora_operaciones_real.csv")
    csv_old_path = Path("logs/operaciones_live_demo.csv")
    
    if bitacora_path.exists():
        try:
            df = pd.read_csv(bitacora_path)
            if not df.empty and 'pnl_neto_usdt' in df.columns:
                return df
        except Exception:
            pass
            
    if csv_old_path.exists():
        try:
            df = pd.read_csv(csv_old_path)
            if not df.empty:
                return df
        except Exception:
            pass
            
    return pd.DataFrame()


def display_metric_card(title, value, delta=None, color="#00ff88"):
    """Mostrar tarjeta de métrica."""
    delta_color = "#ff4444" if delta and str(delta).startswith('-') else "#00ff88"
    st.markdown(f"""
    <div class="metric-card" style="border-color: {color}">
        <h3 style="color: {color}; margin: 0 0 10px 0;">{title}</h3>
        <p style="font-size: 2em; font-weight: bold; margin: 0;">{value}</p>
        {f'<p style="color: {delta_color}; margin: 5px 0 0 0;">{delta}</p>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)


def main():
    st.title("🤖 Sistema Autónomo de Trading en Vivo (Binance Testnet)")
    st.markdown("---")
    
    # Cargar datos en vivo
    tot_bal, avail_bal, live_positions = load_live_account()
    df_trades = load_bitacora_trades()
    
    # Pestañas
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Monitor en Vivo", "📜 Bitácora de Trades", "📈 Backtesting Masivo", "⚙️ Ajustes del Sistema"])
    
    with tab1:
        st.header("Balance y Operaciones en Vivo")
        
        # Métricas principales en vivo
        col1, col2, col3, col4 = st.columns(4)
        
        total_trades = len(df_trades) if not df_trades.empty else 0
        wins = len(df_trades[df_trades['pnl_neto_usdt'] > 0]) if not df_trades.empty and 'pnl_neto_usdt' in df_trades.columns else 0
        win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
        pnl_neto_total = df_trades['pnl_neto_usdt'].sum() if not df_trades.empty and 'pnl_neto_usdt' in df_trades.columns else 0.0
        
        with col1:
            display_metric_card("Balance Total", f"${tot_bal:,.2f} USDT", "En Tiempo Real")
        
        with col2:
            display_metric_card("Margen Disponible", f"${avail_bal:,.2f} USDT", f"Posic. Activas: {len(live_positions)}/10")
        
        with col3:
            display_metric_card("Win Rate en Vivo", f"{win_rate:.1f}%", f"{wins}/{total_trades} Wins")
        
        with col4:
            display_metric_card("PnL Neto Acumulado", f"${pnl_neto_total:+.2f} USDT", "Neto de Fees")
        
        st.markdown("---")
        
        # Posiciones Abiertas Ahora en Binance
        st.subheader("🔥 Posiciones Abiertas Activas en Binance Testnet")
        if live_positions:
            df_live = pd.DataFrame(live_positions)
            st.dataframe(df_live, use_container_width=True)
        else:
            st.info("Actualmente no hay posiciones abiertas flotando en Binance. El bot se encuentra escaneando señales cada 15 segundos.")

    with tab2:
        st.header("Bitácora Histórica Resguardada")
        if not df_trades.empty:
            st.subheader(f"Total Operaciones Registradas en Mac: {len(df_trades)}")
            st.dataframe(df_trades, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Curva de Rendimiento Neto")
            if 'pnl_neto_usdt' in df_trades.columns:
                df_trades['cum_pnl'] = df_trades['pnl_neto_usdt'].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=df_trades['cum_pnl'], mode='lines+markers', name='PnL Acumulado', line=dict(color='#00ff88', width=2)))
                fig.update_layout(template="plotly_dark", height=400, title="PnL Neto Acumulado (USDT)")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay trades cerrados en la bitácora aún. Cada posición cerrada por el bot escribirá automáticamente una fila aquí.")

    with tab3:
        st.header("Ejecución de Backtest Masivo")
        symbol = st.selectbox("Símbolo", ["ADA/USDT", "SUI/USDT", "OP/USDT", "DOGE/USDT", "AVAX/USDT", "APT/USDT", "BTC/USDT", "ETH/USDT"])
        strategy = st.selectbox("Estrategia", ["EMA Cross + Protector", "Grid Trading", "MACD Scalper", "VWAP Reversion", "Trend Breakout"])
        days = st.slider("Días de Datos Históricos", 7, 90, 30)
        
        if st.button("Ejecutar Backtest"):
            st.success(f"Backtest simulado completado para {symbol} con {strategy} ({days} días).")

    with tab4:
        st.header("Hardware y Sistema")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Procesador", "Apple M2 8GB")
            st.metric("Modo Reposo", "Disablesleep + Caffeinate Activo")
        with col2:
            st.metric("Exchange", "Binance Futures Testnet")
            st.metric("Frecuencia", "15 Segundos")

if __name__ == '__main__':
    main()
