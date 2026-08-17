# 🛡️ PROTOCOLO MAESTRO DE RECUPERACIÓN CATASTRÓFICA (GUÍA DE REACTIVACIÓN RÁPIDA)

> **PROPÓSITO**: Esta guía contiene todas las instrucciones y comandos necesarios para volver a levantar el ecosistema completo de trading cuantitativo en caso de que la Mac se apague por batería, corte de energía o fallo del sistema.

---

## ⚡ 1. RECUPERACIÓN EN UN SOLO COMANDO (MÉTODO RÁPIDO RECOMENDADO)

Abre la terminal en tu Mac y ejecuta el siguiente comando único:

```bash
cd /Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system && bash scripts/recuperar_sistema_completo.sh
```

Este script automático realiza:
1. Verificación y activación del entorno virtual de Python (`venv`).
2. Comprobación y carga de credenciales seguras en `.env` (Binance Testnet e IQ Option).
3. Verificación de conexiones con los exchanges.
4. Auto-limpieza de posiciones huérfanas con riesgo excesivo.
5. Lanzamiento en segundo plano protegido con `caffeinate` (para que puedas cerrar la tapa de la Mac sin que se suspenda el sistema).
6. Ejecución del informe de auditoría y reconciliación en tiempo real.

---

## 🔧 2. RECUPERACIÓN MANUAL PASO A PASO (MÉTODO DETALLADO)

Si deseas levantar cada componente de forma individual o auditar el estado del sistema manualmente:

### Paso 1: Ir a la carpeta del proyecto y activar el entorno
```bash
cd /Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system
source venv/bin/activate
```

### Paso 2: Auditar el estado actual de las cuentas y posiciones abiertas
```bash
python scripts/analisis_multimotor_avanzado.py
```

### Paso 3: Iniciar los 3 Motores Cuantitativos bajo `caffeinate`
Abre terminales separadas o ejecuta en segundo plano:

1. **Motor 1: Arbitraje Estadístico Market-Neutral (Binance Futures)**:
   ```bash
   caffeinate python src/execution/pairs_trading_live_runner.py &
   ```
2. **Motor 2: Bot de Opciones Binarias de Alta Probabilidad (IQ Option Practice)**:
   ```bash
   caffeinate python src/execution/iqoption_live_runner.py &
   ```
3. **Motor 3: Matriz de Régimen Cuantitativa (Binance Futures)**:
   ```bash
   caffeinate python src/execution/multi_asset_portfolio_runner.py &
   ```

---

## 📁 3. UBICACIÓN DE BITÁCORAS Y LOGS FÍSICOS

Todos los registros se guardan en tu Mac para siempre en las siguientes rutas:

- **Pairs Trading Stat-Arb**: `logs/stat_arb/bitacora_pairs_trading.csv`
- **IQ Option Practice Demo**: `logs/iqoption/bitacora_iqoption_practice.csv`
- **Binance Futures Live**: `logs/bitacora_operaciones_real.csv`
- **Historial de Terminal**: `logs/historial_terminal_real.log`

---

## 🛡️ 4. CONFIGURACIÓN ANTI-REPOSO PERMANENTE EN MAC

Para asegurar que la Mac no se apague al cerrar la tapa cuando esté conectada a la corriente, asegúrate de tener activadas estas opciones en macOS:

```bash
sudo pmset -a disablesleep 1
sudo pmset -a autorestart 1
sudo pmset -a womp 1
```
