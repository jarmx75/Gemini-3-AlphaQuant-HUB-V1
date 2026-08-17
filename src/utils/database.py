"""
Database Module
Gestión de base de datos SQLite para el sistema de trading.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, List, Dict
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingDatabase:
    """Gestor de base de datos SQLite para trading."""
    
    def __init__(self, db_path: str = 'data/trading.db'):
        """
        Inicializar base de datos.
        
        Args:
            db_path: Ruta del archivo SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._initialize_db()
        logger.info(f"Base de datos inicializada en {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtener conexión a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_db(self):
        """Crear tablas iniciales."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    strategy TEXT NOT NULL,
                    pnl REAL,
                    fees REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de positions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL,
                    unrealized_pnl REAL,
                    strategy TEXT NOT NULL,
                    opened_at DATETIME NOT NULL,
                    closed_at DATETIME,
                    status TEXT DEFAULT 'open',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de strategy_performance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(strategy, date)
                )
            """)
            
            # Tabla de market_data_summary
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    timeframe TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, timeframe)
                )
            """)
            
            # Tabla de system_logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Tablas creadas/verificadas exitosamente")
    
    def insert_trade(self, trade_data: Dict) -> int:
        """
        Insertar un trade en la base de datos.
        
        Args:
            trade_data: Dict con datos del trade
            
        Returns:
            ID del trade insertado
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (symbol, side, quantity, price, timestamp, strategy, pnl, fees)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data['symbol'],
                trade_data['side'],
                trade_data['quantity'],
                trade_data['price'],
                trade_data['timestamp'],
                trade_data['strategy'],
                trade_data.get('pnl'),
                trade_data.get('fees', 0)
            ))
            conn.commit()
            logger.info(f"Trade insertado: {trade_data['symbol']} {trade_data['side']}")
            return cursor.lastrowid
    
    def insert_position(self, position_data: Dict) -> int:
        """
        Insertar una posición en la base de datos.
        
        Args:
            position_data: Dict con datos de la posición
            
        Returns:
            ID de la posición insertada
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO positions (symbol, side, quantity, entry_price, current_price, 
                                       unrealized_pnl, strategy, opened_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data['symbol'],
                position_data['side'],
                position_data['quantity'],
                position_data['entry_price'],
                position_data.get('current_price'),
                position_data.get('unrealized_pnl', 0),
                position_data['strategy'],
                position_data['opened_at'],
                position_data.get('status', 'open')
            ))
            conn.commit()
            logger.info(f"Posición insertada: {position_data['symbol']} {position_data['side']}")
            return cursor.lastrowid
    
    def update_position(self, position_id: int, update_data: Dict) -> bool:
        """
        Actualizar una posición.
        
        Args:
            position_id: ID de la posición
            update_data: Dict con campos a actualizar
            
        Returns:
            True si exitoso
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Construir query dinámico
            set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values()) + [position_id]
            
            cursor.execute(f"""
                UPDATE positions 
                SET {set_clause}
                WHERE id = ?
            """, values)
            
            conn.commit()
            logger.info(f"Posición {position_id} actualizada")
            return True
    
    def get_open_positions(self, strategy: Optional[str] = None) -> List[Dict]:
        """
        Obtener posiciones abiertas.
        
        Args:
            strategy: Filtrar por estrategia (opcional)
            
        Returns:
            Lista de posiciones abiertas
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if strategy:
                cursor.execute("""
                    SELECT * FROM positions 
                    WHERE status = 'open' AND strategy = ?
                    ORDER BY opened_at DESC
                """, (strategy,))
            else:
                cursor.execute("""
                    SELECT * FROM positions 
                    WHERE status = 'open'
                    ORDER BY opened_at DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Obtener trades como DataFrame.
        
        Args:
            symbol: Filtrar por símbolo
            strategy: Filtrar por estrategia
            limit: Límite de registros
            
        Returns:
            DataFrame con trades
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if strategy:
                query += " AND strategy = ?"
                params.append(strategy)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
    
    def log_system_event(self, level: str, message: str, module: Optional[str] = None):
        """
        Registrar evento del sistema.
        
        Args:
            level: Nivel de log (INFO, WARNING, ERROR)
            message: Mensaje del evento
            module: Módulo que genera el evento
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_logs (level, message, module)
                VALUES (?, ?, ?)
            """, (level, message, module))
            conn.commit()
    
    def get_strategy_performance(self, strategy: str, days: int = 30) -> pd.DataFrame:
        """
        Obtener performance de una estrategia.
        
        Args:
            strategy: Nombre de la estrategia
            days: Días a considerar
            
        Returns:
            DataFrame con métricas de performance
        """
        with self._get_connection() as conn:
            query = """
                SELECT * FROM strategy_performance 
                WHERE strategy = ? AND date >= date('now', ?)
                ORDER BY date DESC
            """
            df = pd.read_sql_query(query, conn, params=[strategy, f"-{days} days"])
            return df
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Crear backup de la base de datos.
        
        Args:
            backup_path: Ruta del backup
            
        Returns:
            True si exitoso
        """
        try:
            import shutil
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup creado en {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return False


def main():
    """Función principal para testing."""
    # Crear base de datos
    db = TradingDatabase('data/trading.db')
    
    # Insertar trade de prueba
    trade_data = {
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'quantity': 0.001,
        'price': 50000.0,
        'timestamp': datetime.now(),
        'strategy': 'test_strategy',
        'pnl': 100.0,
        'fees': 5.0
    }
    
    trade_id = db.insert_trade(trade_data)
    print(f"Trade insertado con ID: {trade_id}")
    
    # Obtener trades
    trades = db.get_trades(limit=5)
    print(f"\nTrades en base de datos:")
    print(trades)
    
    # Log de evento
    db.log_system_event('INFO', 'Sistema iniciado correctamente', 'database')


if __name__ == '__main__':
    main()
