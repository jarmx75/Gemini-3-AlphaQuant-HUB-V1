"""
Live Demo Execution Module (Binance Futures Testnet)
Ejecutor autónomo en tiempo real para Binance Demo, integrado en el proyecto DEVIN.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Importar binance UMFutures
try:
    from binance.um_futures import UMFutures
except ImportError:
    UMFutures = None

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.backtesting.indicators import add_all_indicators
from src.strategies.ema_cross_protector import EMACrossProtectorStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveDemoRunner:
    """Ejecutor de Trading Autónomo en Binance Futures Testnet."""
    
    def __init__(self, config_path: str = "config/live_config.json"):
        self.config_path = config_path
        self.load_config()
        self.init_client()
        self.open_positions = {}
        self.strategy = EMACrossProtectorStrategy()
        
    def load_config(self):
        """Cargar variables de entorno y configuración."""
        # Buscar .env en el proyecto actual o en Rowboat_Binance
        possible_envs = [
            Path('.env'),
            Path('../Rowboat_Binance/.env'),
            Path('/Users/jorgeatilano/Desktop/Antigravity_Trading/Rowboat_Binance/.env')
        ]
        for env_file in possible_envs:
            if env_file.exists():
                load_dotenv(env_file)
                logger.info(f"Cargado entorno desde {env_file}")
                break
                
        self.api_key = os.getenv('BINANCE_API_KEY') or os.getenv('BINANCE_DEMO_API_KEY', '')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY') or os.getenv('BINANCE_DEMO_SECRET_KEY', '')
        
        # Símbolos activos predeterminados
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'LTCUSDT',
            'WIFUSDT', 'LINKUSDT', 'AAVEUSDT', 'ADAUSDT', 'AVAXUSDT'
        ]
        self.leverage = 10
        self.risk_pct = 0.01  # 1% por trade
        self.max_positions = 5
        
    def init_client(self):
        """Inicializar cliente UMFutures Testnet."""
        if UMFutures is None:
            logger.error("Librería python-binance no instalada. Ejecute: pip install python-binance")
            return
            
        # Testnet URL oficial de Binance Futures
        self.client = UMFutures(
            key=self.api_key,
            secret=self.secret_key,
            base_url='https://testnet.binancefuture.com'
        )
        logger.info("Cliente Binance Futures Testnet inicializado correctamente.")
        
    def get_account_balance((self) -> float:
        """Obtener saldo disponible USDT."""
        try:
            acc = self.client.account(recvWindow=60000)
            return float(acc.get('availableBalance', 10000.0))
        except Exception as e:
            logger.error(f"Error leyendo balance account(): {e}")
            return 10000.0
            
    def fetch_recent_klines(self, symbol: str, timeframe: str = '15m', limit: int = 250) -> pd.DataFrame:
        """Obtener últimas velas para análisis cuantitativo."""
        try:
            raw = self.client.klines(symbol=symbol, interval=timeframe, limit=limit)
            df = pd.DataFrame(raw, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df.set_index('timestamp', inplace=True)
            return add_all_indicators(df)
        except Exception as e:
            logger.error(f"Error descargando klines para {symbol}: {e}")
            return pd.DataFrame()

    def run_loop(self):
        """Bucle principal de ejecución desacoplada."""
        logger.info("🚀 INICIANDO BUCLE AUTÓNOMO LIVE DEMO (DEVIN SYSTEM)")
        
        while True:
            try:
                balance = self.get_account_balance()
                logger.info(f"⚡ [PULSO DE TRADING] Balance USDT: ${balance:.2f} | Posiciones Activas: {len(self.open_positions)}/{self.max_positions}")
                
                # Evaluar cada símbolo
                for symbol in self.symbols:
                    df = self.fetch_recent_klines(symbol, '15m')
                    if df.empty or len(df) < 200:
                        continue
                        
                    open_pos = self.open_positions.get(symbol)
                    signal = self.strategy.generate_signal(df, open_pos)
                    
                    if signal:
                        action = signal['action']
                        reason = signal.get('reason', '')
                        logger.info(f"🎯 SEÑAL DETECTADA en {symbol}: {action.upper()} ({reason})")
                        
                        if action == 'buy' and len(self.open_positions) < self.max_positions:
                            curr_price = df.iloc[-1]['close']
                            qty = (balance * self.risk_pct * self.leverage) / curr_price
                            self.open_positions[symbol] = {
                                'side': 'long',
                                'entry_price': curr_price,
                                'highest_price': curr_price,
                                'lowest_price': curr_price,
                                'quantity': qty,
                                'entry_time': datetime.now()
                            }
                            logger.info(f"✅ LONG Simulado/Demo Ejecutado: {symbol} Qty={qty:.4f} @ ${curr_price:.2f}")
                            
                        elif action == 'close' and symbol in self.open_positions:
                            curr_price = df.iloc[-1]['close']
                            entry = self.open_positions[symbol]['entry_price']
                            pnl = (curr_price - entry) * self.open_positions[symbol]['quantity'] if self.open_positions[symbol]['side'] == 'long' else (entry - curr_price) * self.open_positions[symbol]['quantity']
                            logger.info(f"🛑 POSICIÓN CERRADA: {symbol} PnL=${pnl:.2f} Razón={reason}")
                            del self.open_positions[symbol]
                            
                time.sleep(15)  # Escaneo cada 15 segundos
                
            except KeyboardInterrupt:
                logger.info("Detención manual recibida.")
                break
            except Exception as e:
                logger.error(f"Excepción en bucle live runner: {e}")
                time.sleep(10)


if __name__ == '__main__':
    runner = LiveDemoRunner()
    runner.run_loop()
