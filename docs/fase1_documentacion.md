# Fase 1: Infraestructura de Datos y Backtesting

## Objetivo
Construir la base de datos y el pipeline de recolección de datos sin IA, optimizado para MacBook Air M2 (8GB RAM).

## Componentes Implementados

### 1. Sistema de Data Collection (`src/data/data_collector.py`)

**Funcionalidades:**
- Recolecta datos OHLCV de exchanges usando CCXT
- Soporta múltiples exchanges (Binance, Bybit, etc.)
- Descarga datos históricos en chunks
- Almacenamiento eficiente en formato Parquet
- Recolecta order books y funding rates

**Clases principales:**
- `DataCollector`: Clase principal para recolección de datos
- `HistoricalDataDownloader`: Descarga datos históricos automáticos

**Uso básico:**
```python
from src.data.data_collector import DataCollector, HistoricalDataDownloader

# Crear colector
collector = DataCollector('binance', sandbox=True)

# Descargar datos históricos
downloader = HistoricalDataDownloader(collector)
filepath = downloader.download_historical_data('BTC/USDT', '1h', days=30)
```

### 2. Sistema de Base de Datos (`src/utils/database.py`)

**Funcionalidades:**
- Base de datos SQLite para persistencia
- Tablas para trades, positions, strategy performance
- Logging de eventos del sistema
- Backup integrado de base de datos

**Tablas:**
- `trades`: Registro de todas las operaciones
- `positions`: Posiciones abiertas/cerradas
- `strategy_performance`: Métricas por estrategia
- `market_data_summary`: Resumen de datos de mercado
- `system_logs`: Logs del sistema

**Uso básico:**
```python
from src.utils.database import TradingDatabase

db = TradingDatabase('data/trading.db')

# Insertar trade
trade_data = {
    'symbol': 'BTC/USDT',
    'side': 'buy',
    'quantity': 0.001,
    'price': 50000.0,
    'timestamp': datetime.now(),
    'strategy': 'test_strategy'
}
db.insert_trade(trade_data)
```

### 3. Sistema de Respaldos (`src/utils/backup_manager.py`)

**Funcionalidades:**
- Backups completos del proyecto
- Backups específicos de base de datos
- Backups de configuraciones
- Limpieza automática de backups antiguos
- Compresión con gzip

**Tipos de backup:**
- Full backup: Todo el proyecto (src, config, data, docs)
- Database backup: Solo la base de datos SQLite
- Config backup: Configuraciones del sistema

**Uso básico:**
```python
from src.utils.backup_manager import BackupManager

backup_manager = BackupManager(
    project_root='/path/to/project',
    backup_dir='backups',
    retention_days=30
)

# Backup diario
results = backup_manager.create_daily_backup()
```

## Estructura de Directorios

```
trading-autonomous-system/
├── src/
│   ├── data/
│   │   └── data_collector.py      # Recolector de datos
│   └── utils/
│       ├── database.py            # Gestión de SQLite
│       └── backup_manager.py      # Sistema de backups
├── data/
│   ├── raw/                       # Datos crudos en Parquet
│   └── processed/                 # Datos procesados
├── config/
│   ├── requirements.txt           # Dependencias Python
│   └── .env.example              # Variables de entorno
├── backups/                       # Respaldos automatizados
├── logs/                          # Logs del sistema
└── docs/                          # Documentación
```

## Instalación

### 1. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 2. Instalar dependencias
```bash
pip install -r config/requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp config/.env.example config/.env
# Editar config/.env con tus API keys
```

## Testing

### Test de recolección de datos
```bash
python src/data/data_collector.py
```

### Test de base de datos
```bash
python src/utils/database.py
```

### Test de backups
```bash
python src/utils/backup_manager.py
```

## Verificación

### Checklist de verificación Fase 1:
- [ ] Data collector descarga datos de Binance sandbox
- [ ] Datos se guardan en formato Parquet
- [ ] Base de datos SQLite se inicializa correctamente
- [ ] Se pueden insertar y consultar trades
- [ ] Sistema de backups crea archivos comprimidos
- [ ] Backups antiguos se eliminan automáticamente
- [ ] Todo funciona en MacBook Air M2 (8GB RAM)

## Optimizaciones para M2 (8GB RAM)

1. **Parquet sobre CSV:** Compresión eficiente, menor uso de RAM
2. **SQLite sobre PostgreSQL:** Ligero, sin servidor dedicado
3. **Chunks en descarga:** Evitar sobrecarga de memoria
4. **Rate limiting:** Respetar límites de API
5. **Logs en archivo:** No saturar memoria

## Próximos Pasos (Fase 1.5)

1. Implementar motor de backtesting determinista
2. Crear indicadores técnicos básicos
3. Implementar primera estrategia simple (grid trading)
4. Crear script de recolección automatizada (cron job)

## Notas Importantes

- Todo el código es determinista, sin IA por ahora
- Enfoque en simplicidad y verificabilidad (Método Karpathy)
- Código listo para escalar cuando se tenga DGX Spark
- Documentación completa para facilitar migración
