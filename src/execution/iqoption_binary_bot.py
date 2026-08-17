"""
IQ Option Quantitative Binary Options Engine (Practice / Demo Mode)
Estrategia de Micro-Estructura: Reversión en Bandas de Bollinger (2.2 sigma) + Estocástico + RSI Extremo
Gestión de Capital: Criterio Fraccional de Kelly (Anti-Martingala).
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

# Configuración de Logging
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class IQOptionBinaryBot:
    """Bot Cuantitativo de Alta Probabilidad para IQ Option (Modo Práctica/Demo)."""
    
    def __init__(self, balance_mode: str = "PRACTICE"):
        self.load_env()
        self.balance_mode = balance_mode  # "PRACTICE" (Demo) o "REAL"
        self.client = None
        self.active_pairs = ['EURUSD-OTC', 'GBPUSD-OTC', 'USDJPY-OTC', 'AUDUSD-OTC', 'EURGBP-OTC', 'BTCUSD']
        self.csv_log_path = Path("logs/iqoption/bitacora_iqoption_practice.csv")
        self.init_csv()
        
        # Parámetros Cuantitativos de Micro-Estructura Calibrados
        self.bb_period = 20
        self.bb_std = 2.2        # 2.2 Desviaciones Estándar para alta probabilidad y frecuencia óptima
        self.rsi_period = 14
        self.rsi_oversold = 28.0 # Sobreventa < 28
        self.rsi_overbought = 72.0 # Sobrecompra > 72
        self.stoch_period = 14
        self.duration_min = 1    # Expiración a 1 minuto
        self.max_trade_usd = 25.0 # Límite máximo por trade en demo
        
    def init_csv(self):
        if not self.csv_log_path.exists():
            with open(self.csv_log_path, "w", encoding="utf-8") as f:
                f.write("timestamp,pair,direction,duration_min,amount_usd,order_id,result,profit_usd,balance_after\n")

    def load_env(self):
        possible_envs = [
            Path('.env'),
            Path('../Rowboat_Binance/.env'),
            Path('/Users/jorgeatilano/Desktop/Antigravity_Trading/Rowboat_Binance/.env')
        ]
        for env_file in possible_envs:
            if env_file.exists():
                load_dotenv(env_file)
                break
        self.email = os.getenv('IQ_OPTION_EMAIL', '')
        self.password = os.getenv('IQ_OPTION_PASSWORD', '')

    def connect(self) -> bool:
        """Establece conexión con IQ Option API."""
        try:
            from iqoptionapi.stable_api import IQ_Option
            if not self.email or not self.password:
                logger.warning("⚠️ Credenciales IQ Option no configuradas en .env.")
                return False
                
            self.client = IQ_Option(self.email, self.password)
            check, reason = self.client.connect()
            if check:
                self.client.change_balance(self.balance_mode)
                bal = self.client.get_balance()
                logger.info(f"✅ Conectado a IQ Option en Modo {self.balance_mode} | Balance: ${bal:.2f}")
                return True
            else:
                logger.error(f"❌ Error al conectar a IQ Option: {reason}")
                return False
        except Exception as e:
            logger.error(f"❌ Error de importación o conexión IQ Option: {e}")
            return False

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula Bandas de Bollinger 2.2 sigma, RSI y Estocástico."""
        df['sma'] = df['close'].rolling(window=self.bb_period).mean()
        df['std'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['sma'] + (self.bb_std * df['std'])
        df['bb_lower'] = df['sma'] - (self.bb_std * df['std'])
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Estocástico %K y %D
        low_min = df['low'].rolling(window=self.stoch_period).min()
        high_max = df['high'].rolling(window=self.stoch_period).max()
        df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min + 1e-9))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        return df

    def calculate_kelly_bet(self, balance: float, win_rate: float = 0.62, payout: float = 0.85) -> float:
        """
        Calcula el tamaño óptimo de apuesta usando el Criterio Fraccional de Kelly (0.05 f*).
        """
        p = win_rate
        q = 1.0 - p
        b = payout
        f_star = (p * b - q) / b
        
        if f_star <= 0:
            return 1.0  # Mínimo $1
            
        fractional_kelly = f_star * 0.05  # 5% del Kelly óptimo para baja varianza
        bet_amount = round(balance * fractional_kelly, 2)
        return float(np.clip(bet_amount, 1.0, self.max_trade_usd))

    def evaluate_pair_signal(self, df: pd.DataFrame) -> Optional[str]:
        """
        Evalúa si una vela de 1m toca la banda Bollinger de 2.2 sigma con confirmación de oscilador.
        
        Returns:
            'call' (Compra/Sube), 'put' (Venta/Baja) o None.
        """
        if len(df) < self.bb_period + 5:
            return None
            
        df = self.calculate_indicators(df)
        curr = df.iloc[-1]
        
        # CALL: Precio toca banda inferior (2.2 sigma) con RSI <= 28 o Estocástico en sobreventa con cruce alcista
        call_cond = (curr['low'] <= curr['bb_lower']) and (curr['rsi'] <= self.rsi_oversold or (curr['stoch_k'] <= 25 and curr['stoch_k'] > curr['stoch_d']))
        if call_cond:
            return 'call'
            
        # PUT: Precio toca banda superior (2.2 sigma) con RSI >= 72 o Estocástico en sobrecompra con cruce bajista
        put_cond = (curr['high'] >= curr['bb_upper']) and (curr['rsi'] >= self.rsi_overbought or (curr['stoch_k'] >= 75 and curr['stoch_k'] < curr['stoch_d']))
        if put_cond:
            return 'put'
            
        return None
