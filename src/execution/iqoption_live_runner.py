"""
IQ Option Quantitative Binary Options Autonomous Live Runner (Practice / Demo Mode)
Conectado 100% a la API de IQ Option:
  - Detecta pares activos en vivo (OTC y regulares).
  - Descarga velas reales de 1m desde los servidores de IQ Option sin caídas de conexión.
  - Evalúa la micro-estructura de reversión en Bandas de Bollinger 2.2 sigma + Estocástico + RSI Extremo.
  - Envía órdenes REALES en cuenta Practice con Criterio de Kelly.
  - Registra cada operación y su resultado verificado en logs/iqoption/bitacora_iqoption_practice.csv.
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

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent.parent))
from iqoptionapi.stable_api import IQ_Option
from src.execution.iqoption_binary_bot import IQOptionBinaryBot

# Directorio de Logs
log_dir = Path("logs/iqoption")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/iqoption/historial_iqoption_practice.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IQOptionLiveRunner:
    """Ejecutor Continuo Real para IQ Option Demo."""
    
    def __init__(self):
        load_dotenv()
        self.email = os.getenv('IQ_OPTION_EMAIL', '')
        self.password = os.getenv('IQ_OPTION_PASSWORD', '')
        self.bot = IQOptionBinaryBot(balance_mode="PRACTICE")
        
        # Pares candidatos verificados en OP_code.ACTIVES
        self.pairs = [
            'EURUSD-OTC', 'GBPUSD-OTC', 'USDJPY-OTC', 
            'EURGBP-OTC', 'EURJPY-OTC', 'USDCHF-OTC', 'BTCUSD',
            'EURUSD', 'GBPUSD', 'USDJPY', 'EURGBP', 'EURJPY'
        ]
        self.csv_log_path = Path("logs/iqoption/bitacora_iqoption_practice.csv")
        self.init_csv()
        self.connect()

    def init_csv(self):
        if not self.csv_log_path.exists():
            with open(self.csv_log_path, "w", encoding="utf-8") as f:
                f.write("timestamp,pair,direction,duration_min,amount_usd,order_id,result,profit_usd,balance_after\n")

    def connect(self):
        logger.info(f"Conectando a IQ Option ({self.email})...")
        self.api = IQ_Option(self.email, self.password)
        check, reason = self.api.connect()
        if check:
            self.api.change_balance('PRACTICE')
            bal = self.api.get_balance()
            logger.info(f"✅ Conexión EXITOSA a IQ Option en MODO PRACTICE | Balance Actual: ${bal:.2f} USD")
            return True
        else:
            logger.error(f"❌ Fallo conectando a IQ Option: {reason}")
            return False

    def fetch_live_candles(self, pair: str) -> pd.DataFrame:
        """Obtiene las últimas 40 velas reales de 1m desde los servidores de IQ Option."""
        try:
            raw_candles = self.api.get_candles(pair, 60, 40, int(time.time()))
            if not raw_candles:
                return pd.DataFrame()
            df = pd.DataFrame(raw_candles)
            df['close'] = df['close'].astype(float)
            df['open'] = df['open'].astype(float)
            df['high'] = df['max'].astype(float)
            df['low'] = df['min'].astype(float)
            return df
        except Exception as e:
            return pd.DataFrame()

    def run_loop(self):
        logger.info("🎯 INICIANDO MOTOR CUANTITATIVO REAL DE OPCIONES BINARIAS IQ OPTION (PRACTICE)")
        
        while True:
            try:
                if not self.api.check_connect():
                    logger.warning("⚠️ Websocket desconectado de IQ Option. Re-conectando...")
                    self.connect()
                    time.sleep(3)
                    
                current_bal = self.api.get_balance()
                logger.info(f"📊 [PULSO IQ-OPTION] Balance Practice: ${current_bal:.2f} USD")
                
                for pair in self.pairs:
                    df_candles = self.fetch_live_candles(pair)
                    if df_candles.empty or len(df_candles) < 25:
                        continue
                        
                    signal = self.bot.evaluate_pair_signal(df_candles)
                    
                    if signal in ['call', 'put']:
                        bet_size = self.bot.calculate_kelly_bet(current_bal, win_rate=0.65, payout=0.85)
                        duration = 1  # 1 minuto
                        
                        logger.info(f"🚀 [ORDEN REAL PRACTICE] Par: {pair} | Dirección: {signal.upper()} | Bet: ${bet_size:.2f} USD")
                        buy_check, buy_id = self.api.buy(bet_size, pair, signal, duration)
                        
                        if buy_check:
                            logger.info(f"✅ Orden Ejecutada en IQ Option | OrderID: {buy_id} | Esperando Expiración (65s)...")
                            time.sleep(65)  # Esperar resolución de 1m
                            
                            profit = self.api.check_win_v3(buy_id)
                            result = "WIN" if profit > 0 else ("EQUAL" if profit == 0 else "LOSS")
                            new_bal = self.api.get_balance()
                            
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            with open(self.csv_log_path, "a", encoding="utf-8") as f:
                                f.write(f"{now_str},{pair},{signal.upper()},{duration},{bet_size:.2f},{buy_id},{result},{profit:+.2f},{new_bal:.2f}\n")
                                
                            logger.info(f"🏁 [RESOLUCIÓN REAL] OrderID: {buy_id} -> {result} ({profit:+.2f} USD) | Nuevo Balance: ${new_bal:.2f} USD")
                            
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error en bucle IQ Option: {e}")
                time.sleep(10)

if __name__ == '__main__':
    runner = IQOptionLiveRunner()
    runner.run_loop()
