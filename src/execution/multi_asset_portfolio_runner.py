"""
Multi-Asset & Multi-Strategy Live Demo Portfolio Runner (Binance Futures Testnet Real Execution)
Incluye:
  1. CAP MÁXIMO DE PÉRDIDA POR POSICIÓN ($15.00 USDT MAX LOSS): Cierra inmediatamente cualquier posición si PnL no realizado toca -$15 USDT.
  2. Resincronización Activa con obtención de entryPrice real desde Binance API (Previene discrepancias de $0.00).
  3. Control Estricto de Stop Loss en Grid Trading.
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

try:
    from binance.um_futures import UMFutures
except ImportError:
    UMFutures = None

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.backtesting.indicators import add_all_indicators
from src.execution.smart_portfolio_matrix import SmartPortfolioMatrix

# Configuración de Logging Físico Permanente
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/historial_terminal_real.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MultiAssetPortfolioRunner:
    """Ejecutor de Portafolio Autónomo Multiactivo con Cap Máximo de Riesgo por Posición."""
    
    def __init__(self):
        self.load_env()
        self.matrix = SmartPortfolioMatrix()
        self.init_binance()
        
        self.symbols = [
            'AVAXUSDT', 'LINKUSDT', 'SUIUSDT', 'BNBUSDT', 'SOLUSDT',
            'BTCUSDT', 'DOGEUSDT', 'ARBUSDT', 'APTUSDT', 'FILUSDT',
            'NEARUSDT', 'UNIUSDT', 'DOTUSDT', 'OPUSDT'
        ]
        
        self.open_positions = {}
        self.max_positions = 10
        self.risk_per_trade_pct = 0.010  # 1.0% de riesgo por trade
        self.max_loss_cap_usd = 15.0     # CAP MÁXIMO DE PÉRDIDA PERMITIDA POR TRADE: -$15.00 USDT
        self.leverage = 10
        self.decimals_vol = {}
        self.decimals_price = {}
        
        # Archivos de registro CSV Resguardados
        self.csv_bitacora_path = Path("logs/bitacora_operaciones_real.csv")
        self.csv_summary_path = Path("logs/resumen_diario_live_demo.csv")
        self.init_csv_files()
        self.load_exchange_precisions()
        self.sync_positions_from_exchange()

    def init_csv_files(self):
        """Inicializar archivos CSV con cabeceras completas."""
        if not self.csv_bitacora_path.exists():
            with open(self.csv_bitacora_path, "w", encoding="utf-8") as f:
                f.write("fecha_entrada,fecha_cierre,simbolo,estrategia,lado,cantidad,precio_entrada,precio_cierre,pnl_bruto_usdt,comisiones_usdt,pnl_neto_usdt,pnl_neto_pct,motivo_cierre,order_id_apertura,order_id_cierre\n")
        if not self.csv_summary_path.exists():
            with open(self.csv_summary_path, "w", encoding="utf-8") as f:
                f.write("date,total_trades,winning_trades,win_rate_pct,est_daily_pnl_pct\n")

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
        self.api_key = os.getenv('BINANCE_TEST_KEY') or os.getenv('BINANCE_API_KEY', '')
        self.secret_key = os.getenv('BINANCE_TEST_SECRET') or os.getenv('BINANCE_SECRET_KEY', '')

    def init_binance(self):
        try:
            self.client = UMFutures(
                key=self.api_key,
                secret=self.secret_key,
                base_url='https://testnet.binancefuture.com',
                timeout=20
            )
            logger.info("⚡ Cliente UMFutures Binance Futures Testnet Inicializado Correctamente.")
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente Binance: {e}")
            self.client = None

    def safe_request(self, func, *args, **kwargs):
        """Peticiones seguras a la API de Binance con manejo de reintentos."""
        if func.__name__ in ['new_order', 'account', 'cancel_order', 'query_order', 'balance', 'change_leverage']:
            kwargs['recvWindow'] = 60000
        for _ in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "Read timed out" in str(e) or "-1021" in str(e) or "Remote end closed" in str(e):
                    time.sleep(3)
                else:
                    raise e
        return None

    def load_exchange_precisions(self):
        """Cargar precisión de cantidad y precio para cada símbolo."""
        try:
            info = self.safe_request(self.client.exchange_info)
            if info:
                for s in info['symbols']:
                    sym = s['symbol']
                    self.decimals_vol[sym] = s['quantityPrecision']
                    self.decimals_price[sym] = s['pricePrecision']
                logger.info(f"✅ Precisión de activos cargada para {len(self.decimals_vol)} pares de trading.")
        except Exception as e:
            logger.warning(f"⚠️ Error cargando precisión de exchange_info: {e}")

    def sync_positions_from_exchange(self):
        """Resincroniza las posiciones reales en Binance conservando el entryPrice real de la API."""
        try:
            acc = self.safe_request(self.client.account)
            if not acc or 'positions' not in acc:
                return
                
            real_positions = {}
            for pos in acc['positions']:
                amt = float(pos['positionAmt'])
                if amt != 0:
                    entry_p = float(pos.get('entryPrice', pos.get('entry_price', 0.0)))
                    if entry_p <= 0:
                        try:
                            ticker = self.safe_request(self.client.ticker_price, symbol=pos['symbol'])
                            if ticker:
                                entry_p = float(ticker['price'])
                        except: pass
                    real_positions[pos['symbol']] = {
                        'amt': amt,
                        'entryPrice': entry_p if entry_p > 0 else 1.0
                    }
                    
            # Purgar posiciones locales cerradas externamente
            for sym in list(self.open_positions.keys()):
                if sym not in real_positions:
                    logger.warning(f"⚠️ [SINK] Posición {sym} cerrada externamente en Binance. Removiendo de memoria local...")
                    del self.open_positions[sym]
                    
            # Restaurar posiciones activas
            for sym, data in real_positions.items():
                if sym not in self.open_positions:
                    side = "long" if data['amt'] > 0 else "short"
                    strat_name, _ = self.matrix.get_strategy_for_symbol(sym)
                    self.open_positions[sym] = {
                        'symbol': sym,
                        'strategy': strat_name,
                        'side': side,
                        'entry_price': data['entryPrice'],
                        'quantity': abs(data['amt']),
                        'order_id_open': 'RESTORED_POST_OUTAGE',
                        'entry_time': datetime.now()
                    }
                    logger.info(f"🔄 [SINK] Posición {sym} ({side.upper()}) sincronizada desde Binance @ ${data['entryPrice']:.4f}")
        except Exception as e:
            logger.error(f"Error en resincronización de posiciones: {e}")

    def get_balances(self):
        """Obtener balance total y disponible."""
        try:
            acc = self.safe_request(self.client.account)
            if acc:
                return float(acc['totalWalletBalance']), float(acc['availableBalance'])
        except Exception as e:
            logger.error(f"Error consultando balance: {e}")
        return 5000.0, 5000.0

    def fetch_klines(self, symbol: str, timeframe: str = '15m') -> pd.DataFrame:
        try:
            raw = self.safe_request(self.client.klines, symbol=symbol, interval=timeframe, limit=200)
            if not raw: return pd.DataFrame()
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
            return pd.DataFrame()

    def log_trade_to_bitacora(self, pos: dict, exit_price: float, reason: str, order_id_cierre: str):
        """Registrar operación cerrada en la bitácora física CSV permanente."""
        fecha_entrada = pos['entry_time'].strftime("%Y-%m-%d %H:%M:%S")
        fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        symbol = pos['symbol']
        strategy = pos['strategy']
        side = pos['side']
        qty = pos['quantity']
        entry_price = pos['entry_price']
        order_id_open = pos.get('order_id_open', 'N/A')

        pnl_bruto = (qty * exit_price) - (qty * entry_price) if side == 'long' else (qty * entry_price) - (qty * exit_price)
        comision_apertura = (qty * entry_price) * 0.0004
        comision_cierre = (qty * exit_price) * 0.0004
        comisiones = comision_apertura + comision_cierre
        pnl_neto = pnl_bruto - comisiones
        pnl_neto_pct = (pnl_neto / (qty * entry_price)) * 100.0 if (qty * entry_price) > 0 else 0.0

        linea = f"{fecha_entrada},{fecha_cierre},{symbol},{strategy},{side},{qty},{entry_price:.4f},{exit_price:.4f},{pnl_bruto:.2f},{comisiones:.2f},{pnl_neto:.2f},{pnl_neto_pct:.2f}%,{reason},{order_id_open},{order_id_cierre}\n"
        with open(self.csv_bitacora_path, "a", encoding="utf-8") as f:
            f.write(linea)

    def run_portfolio_loop(self):
        logger.info("🌐 INICIANDO MOTOR DE PORTAFOLIO REAL CON CAP MÁXIMO DE RIESGO DE $15 USDT")
        
        while True:
            try:
                self.sync_positions_from_exchange()
                tot_bal, avail_bal = self.get_balances()
                logger.info(f"📊 [PULSO DE TRADING] Balance USDT: ${tot_bal:.2f} | Posiciones Activas: {len(self.open_positions)}/{self.max_positions}")
                
                # --- 🛡️ ESCANEO GLOBAL DE RIESGO DE TODAS LAS POSICIONES EN BINANCE ---
                acc_info = self.safe_request(self.client.account)
                if acc_info and 'positions' in acc_info:
                    for p in acc_info['positions']:
                        amt = float(p.get('positionAmt', 0))
                        if amt != 0:
                            unrealized = float(p.get('unrealizedProfit', 0))
                            sym = p['symbol']
                            if unrealized <= -self.max_loss_cap_usd:
                                logger.warning(f"🚨 [GLOBAL CAP RIESGO] {sym} PnL={unrealized:.2f} USDT <= -${self.max_loss_cap_usd}. Cierre Inmediato...")
                                side_cierre = "SELL" if amt > 0 else "BUY"
                                self.safe_request(self.client.new_order, symbol=sym, side=side_cierre, type="MARKET", quantity=abs(amt))
                                if sym in self.open_positions:
                                    del self.open_positions[sym]
                
                for symbol in self.symbols:
                    df = self.fetch_klines(symbol, '15m')
                    if df.empty or len(df) < 100:
                        continue
                        
                    curr_price = df.iloc[-1]['close']
                    open_pos = self.open_positions.get(symbol)
                    
                    # --- 🛡️ CIRCUITO DE SEGURIDAD ABSOLUTA: CAP MÁXIMO DE PÉRDIDA POR TRADE ($15.00 USDT) ---
                    if open_pos:
                        qty = open_pos['quantity']
                        entry_p = open_pos['entry_price']
                        side = open_pos['side']
                        unrealized_pnl = (curr_price - entry_p) * qty if side == 'long' else (entry_p - curr_price) * qty
                        
                        if unrealized_pnl <= -self.max_loss_cap_usd:
                            logger.warning(f"🚨 [CAP RIESGO ALCANZADO] {symbol} flotó en {unrealized_pnl:.2f} USDT (Cap max -${self.max_loss_cap_usd}). Cierre de Emergencia...")
                            side_cierre = "SELL" if side == 'long' else "BUY"
                            res = self.safe_request(self.client.new_order, symbol=symbol, side=side_cierre, type="MARKET", quantity=qty, reduceOnly="true")
                            if res:
                                order_id_cierre = res.get('orderId', 'EMERGENCY_CAP')
                                self.log_trade_to_bitacora(open_pos, curr_price, "MAX_LOSS_CAP_PROTECTION", order_id_cierre)
                                del self.open_positions[symbol]
                                continue

                    strat_name, strat_obj = self.matrix.get_strategy_for_symbol(symbol, df)
                    signal = strat_obj.generate_signal(df, open_pos)
                    
                    if signal:
                        action = signal['action']
                        reason = signal.get('reason', '')
                        
                        if action == 'buy' and symbol not in self.open_positions:
                            if len(self.open_positions) < self.max_positions:
                                self.safe_request(self.client.change_leverage, symbol=symbol, leverage=self.leverage)
                                
                                risk_usd = tot_bal * self.risk_per_trade_pct
                                notional_usd = min(risk_usd * 8, 320.0)  # Límite máximo notional por trade: $320 USD
                                qty = round(notional_usd / curr_price, self.decimals_vol.get(symbol, 2))
                                
                                if qty > 0:
                                    res = self.safe_request(self.client.new_order, symbol=symbol, side="BUY", type="MARKET", quantity=qty)
                                    if res:
                                        order_id = res.get('orderId', 'UNKNOWN')
                                        self.open_positions[symbol] = {
                                            'symbol': symbol,
                                            'strategy': strat_name,
                                            'side': 'long',
                                            'entry_price': curr_price,
                                            'quantity': qty,
                                            'order_id_open': order_id,
                                            'entry_time': datetime.now()
                                        }
                                        logger.info(f"🚀 [{symbol} -> {strat_name}] ✅ BUY REAL EJECUTADO | OrderID: {order_id} | Cant: {qty} @ ${curr_price:.4f}")
                            
                        elif action == 'close' and symbol in self.open_positions:
                            pos = self.open_positions[symbol]
                            qty = pos['quantity']
                            side_cierre = "SELL" if pos['side'] == 'long' else "BUY"
                            
                            res = self.safe_request(self.client.new_order, symbol=symbol, side=side_cierre, type="MARKET", quantity=qty, reduceOnly="true")
                            if res:
                                order_id_cierre = res.get('orderId', 'UNKNOWN')
                                self.log_trade_to_bitacora(pos, curr_price, reason, order_id_cierre)
                                logger.info(f"🛑 [{symbol} -> {strat_name}] CIERRE REAL EJECUTADO | OrderID: {order_id_cierre} | Exit @ ${curr_price:.4f} | Razón: {reason}")
                                del self.open_positions[symbol]
                                
                time.sleep(15)
                
            except KeyboardInterrupt:
                logger.info("Deteniendo ejecutor de portafolio...")
                break
            except Exception as e:
                logger.error(f"Error en bucle principal: {e}")
                time.sleep(10)

if __name__ == '__main__':
    runner = MultiAssetPortfolioRunner()
    runner.run_portfolio_loop()
