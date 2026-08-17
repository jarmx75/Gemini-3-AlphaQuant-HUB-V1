"""
Statistical Arbitrage & Cointegration Pairs Trading Autonomous Live Runner (Market Neutral Beta = 0)
Ejecuta pares de trading cointegrados en Binance Futures Testnet (ej. AVAX/SOL, SUI/APT, LINK/DOT).
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv

try:
    from binance.um_futures import UMFutures
except ImportError:
    UMFutures = None

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.strategies.pairs_trading_stat_arb import PairsTradingStatArb

# Directorio de Logs
log_dir = Path("logs/stat_arb")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/stat_arb/historial_pairs_trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PairsTradingLiveRunner:
    """Ejecutor de Arbitraje Estadístico Market-Neutral."""
    
    def __init__(self):
        self.load_env()
        self.engine = PairsTradingStatArb(z_entry=2.0, z_exit=0.2, z_stop=3.5, lookback_period=60)
        self.init_binance()
        
        # Pares correlacionados para cointegración
        self.monitored_pairs = [
            ('AVAXUSDT', 'SOLUSDT'),
            ('SUIUSDT', 'APTUSDT'),
            ('LINKUSDT', 'DOTUSDT'),
            ('BTCUSDT', 'ETHUSDT')
        ]
        
        self.open_pair_positions = {}
        self.leverage = 10
        self.notional_per_leg = 150.0  # $150 USD por pata ($300 total por par market-neutral)
        self.decimals_vol = {}
        self.csv_log_path = Path("logs/stat_arb/bitacora_pairs_trading.csv")
        self.init_csv()
        self.load_precisions()

    def load_precisions(self):
        try:
            info = self.client.exchange_info()
            for s in info['symbols']:
                self.decimals_vol[s['symbol']] = s['quantityPrecision']
        except: pass

    def init_csv(self):
        if not self.csv_log_path.exists():
            with open(self.csv_log_path, "w", encoding="utf-8") as f:
                f.write("fecha_entrada,fecha_cierre,par,lado_spread,simbolo_y,lado_y,precio_entrada_y,precio_cierre_y,simbolo_x,lado_x,precio_entrada_x,precio_cierre_x,gamma,z_entrada,z_cierre,pnl_neto_usdt,motivo_cierre\n")

    def load_env(self):
        load_dotenv()
        self.api_key = os.getenv('BINANCE_TEST_KEY', '')
        self.secret_key = os.getenv('BINANCE_TEST_SECRET', '')

    def init_binance(self):
        try:
            self.client = UMFutures(
                key=self.api_key,
                secret=self.secret_key,
                base_url='https://testnet.binancefuture.com',
                timeout=20
            )
            logger.info("⚡ Conector Binance Testnet para Pairs Trading Inicializado.")
        except Exception as e:
            logger.error(f"Error conectando a Binance: {e}")
            self.client = None

    def fetch_klines(self, symbol: str, interval: str = '15m') -> pd.DataFrame:
        try:
            raw = self.client.klines(symbol=symbol, interval=interval, limit=100)
            if not raw: return pd.DataFrame()
            df = pd.DataFrame(raw, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df.attrs['symbol'] = symbol
            return df
        except Exception as e:
            return pd.DataFrame()

    def close_exact_position(self, symbol: str):
        """Cierra exactamente la cantidad en posición abierta en Binance para evitar errores de precisión."""
        try:
            acc = self.client.account(recvWindow=60000)
            for p in acc['positions']:
                if p['symbol'] == symbol:
                    amt = float(p.get('positionAmt', 0))
                    if amt != 0:
                        side = "SELL" if amt > 0 else "BUY"
                        self.client.new_order(symbol=symbol, side=side, type="MARKET", quantity=abs(amt), recvWindow=60000)
                        logger.info(f"✅ Cierre exacto en exchange ejecutado para {symbol} ({abs(amt)} {side})")
        except Exception as e:
            logger.error(f"Error en cierre exacto de {symbol}: {e}")

    def run_loop(self):
        logger.info("🌐 INICIANDO MOTOR DE ARBITRAJE ESTADÍSTICO MARKET-NEUTRAL (PAIRS TRADING)")
        
        while True:
            try:
                for sym_y, sym_x in self.monitored_pairs:
                    pair_name = f"{sym_y}/{sym_x}"
                    df_y = self.fetch_klines(sym_y, '15m')
                    df_x = self.fetch_klines(sym_x, '15m')
                    
                    if df_y.empty or df_x.empty:
                        continue
                        
                    open_pos = self.open_pair_positions.get(pair_name)
                    signal = self.engine.generate_pair_signal(df_y, df_x, pair_name, open_pos)
                    
                    if signal:
                        action = signal['action']
                        curr_y_price = df_y.iloc[-1]['close']
                        curr_x_price = df_x.iloc[-1]['close']
                        gamma = signal.get('gamma', 1.0)
                        
                        if action in ['OPEN_LONG_SPREAD', 'OPEN_SHORT_SPREAD'] and pair_name not in self.open_pair_positions:
                            dec_y = self.decimals_vol.get(sym_y, 3)
                            dec_x = self.decimals_vol.get(sym_x, 3)
                            qty_y = round(self.notional_per_leg / curr_y_price, dec_y)
                            qty_x = round((self.notional_per_leg * gamma) / curr_x_price, dec_x)
                            
                            if qty_y <= 0:
                                qty_y = round(self.notional_per_leg / curr_y_price, 3)
                            if qty_x <= 0:
                                qty_x = round((self.notional_per_leg * gamma) / curr_x_price, 3)
                            
                            side_y = "BUY" if action == 'OPEN_LONG_SPREAD' else "SELL"
                            side_x = "SELL" if action == 'OPEN_LONG_SPREAD' else "BUY"
                            
                            # Ejecutar ambas patas simultáneamente
                            self.client.new_order(symbol=sym_y, side=side_y, type="MARKET", quantity=qty_y, recvWindow=60000)
                            self.client.new_order(symbol=sym_x, side=side_x, type="MARKET", quantity=qty_x, recvWindow=60000)
                            
                            self.open_pair_positions[pair_name] = {
                                'pair_name': pair_name,
                                'side': action.replace('OPEN_', ''),
                                'sym_y': sym_y, 'lado_y': side_y, 'entry_y': curr_y_price, 'qty_y': qty_y,
                                'sym_x': sym_x, 'lado_x': side_x, 'entry_x': curr_x_price, 'qty_x': qty_x,
                                'gamma': gamma, 'z_entry': signal['z_score'],
                                'entry_time': datetime.now()
                            }
                            logger.info(f"🚀 [STAT-ARB OPEN] Par {pair_name} | {action} | Z-Score: {signal['z_score']:.2f} | Gamma: {gamma:.4f}")
                            
                        elif action == 'CLOSE_PAIR' and pair_name in self.open_pair_positions:
                            pos = self.open_pair_positions[pair_name]
                            
                            # Cerrar pata Y y pata X con la función de cierre exacto
                            self.close_exact_position(pos['sym_y'])
                            self.close_exact_position(pos['sym_x'])
                            
                            pnl_y = (curr_y_price - pos['entry_y']) * pos['qty_y'] if pos['lado_y'] == 'BUY' else (pos['entry_y'] - curr_y_price) * pos['qty_y']
                            pnl_x = (curr_x_price - pos['entry_x']) * pos['qty_x'] if pos['lado_x'] == 'BUY' else (pos['entry_x'] - curr_x_price) * pos['qty_x']
                            total_pnl = pnl_y + pnl_x - 0.40 # Descontar comisiones
                            
                            # Registrar en bitácora física
                            with open(self.csv_log_path, "a", encoding="utf-8") as f:
                                f.write(f"{pos['entry_time'].strftime('%Y-%m-%d %H:%M:%S')},{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{pair_name},{pos['side']},{pos['sym_y']},{pos['lado_y']},{pos['entry_y']:.4f},{curr_y_price:.4f},{pos['sym_x']},{pos['lado_x']},{pos['entry_x']:.4f},{curr_x_price:.4f},{pos['gamma']:.4f},{pos['z_entry']:.2f},{signal['z_score']:.2f},{total_pnl:.2f},{signal['reason']}\n")
                                
                            logger.info(f"🛑 [STAT-ARB CLOSE] Par {pair_name} | Net PnL: ${total_pnl:+.2f} USDT | Razón: {signal['reason']}")
                            del self.open_pair_positions[pair_name]
                            
                time.sleep(20)
            except Exception as e:
                logger.error(f"Error en bucle Stat-Arb: {e}")
                time.sleep(10)

if __name__ == '__main__':
    runner = PairsTradingLiveRunner()
    runner.run_loop()
