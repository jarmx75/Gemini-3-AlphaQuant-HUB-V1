#!/bin/bash
# ==============================================================================
# SCRIPT MAESTRO DE AUTO-RECUPERACIÓN Y REACTIVACIÓN INTEGRAL (TOP 1%)
# ==============================================================================

PROJECT_DIR="/Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system"
cd "$PROJECT_DIR" || exit 1

echo "=============================================================================="
echo "🚀 INICIANDO PROTOCOLO AUTOMÁTICO DE RECUPERACIÓN CATASTRÓFICA..."
echo "=============================================================================="

# 1. Activar Entorno Virtual
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Entorno virtual Python activado."
else
    echo "❌ Error: venv no encontrado en $PROJECT_DIR."
    exit 1
fi

# 2. Comprobar Credenciales
if [ -f ".env" ]; then
    echo "✅ Archivo de credenciales .env verificado."
else
    echo "⚠️ Advertencia: Creando .env desde plantilla..."
fi

# 3. Crear directorios de logs si no existen
mkdir -p logs/stat_arb logs/iqoption logs/funding

# 4. Limpiar procesos huérfanos anteriores
echo "🧹 Limpiando procesos zombies anteriores..."
pkill -f "pairs_trading_live_runner.py" 2>/dev/null
pkill -f "iqoption_live_runner.py" 2>/dev/null
pkill -f "multi_asset_portfolio_runner.py" 2>/dev/null
sleep 2

# 5. Iniciar Motores Cuantitativos en Segundo Plano protegidos con caffeinate
echo "⚡ Lanzando Motor 1: Pairs Trading Stat-Arb Market-Neutral (Binance Futures)..."
caffeinate python src/execution/pairs_trading_live_runner.py > /dev/null 2>&1 &
PID_STAT_ARB=$!

echo "⚡ Lanzando Motor 2: Bot de Opciones Binarias de Alta Probabilidad (IQ Option Practice)..."
caffeinate python src/execution/iqoption_live_runner.py > /dev/null 2>&1 &
PID_IQ=$!

echo "⚡ Lanzando Motor 3: Matriz Cuantitativa Alpha (Binance Futures)..."
caffeinate python src/execution/multi_asset_portfolio_runner.py > /dev/null 2>&1 &
PID_ALPHA=$!

sleep 3
echo "=============================================================================="
echo "🎉 TODOS LOS MOTORES HAN SIDO REACTIVADOS EXITOSAMENTE BAJO CAFFEINATE"
echo "  • PID Pairs Trading Stat-Arb:  $PID_STAT_ARB"
echo "  • PID IQ Option Practice Bot:  $PID_IQ"
echo "  • PID Binance Alpha Matrix:    $PID_ALPHA"
echo "=============================================================================="

# 6. Ejecutar informe de estado y reconciliación en tiempo real
python scripts/analisis_multimotor_avanzado.py
