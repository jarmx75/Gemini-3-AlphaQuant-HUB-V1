#!/bin/bash

# Script de inicialización del proyecto
# Configura el entorno y realiza pruebas iniciales

set -e  # Detener si hay error

echo "========================================="
echo "Inicializando Sistema de Trading Autónomo"
echo "========================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Verificar Python
echo "1. Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python encontrado: $PYTHON_VERSION"
else
    print_error "Python no encontrado. Por favor instala Python 3.8+"
    exit 1
fi

# Crear entorno virtual
echo ""
echo "2. Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Entorno virtual creado"
else
    print_warning "Entorno virtual ya existe"
fi

# Activar entorno virtual
echo ""
echo "3. Activando entorno virtual..."
source venv/bin/activate
print_success "Entorno virtual activado"

# Actualizar pip
echo ""
echo "4. Actualizando pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "Pip actualizado"

# Instalar dependencias
echo ""
echo "5. Instalando dependencias..."
if [ -f "config/requirements.txt" ]; then
    pip install -r config/requirements.txt
    print_success "Dependencias instaladas"
else
    print_error "Archivo config/requirements.txt no encontrado"
    exit 1
fi

# Crear directorios necesarios
echo ""
echo "6. Creando directorios..."
mkdir -p data/raw data/processed logs backups/databases backups/configs
print_success "Directorios creados"

# Configurar archivo .env
echo ""
echo "7. Configurando variables de entorno..."
if [ ! -f "config/.env" ]; then
    cp config/.env.example config/.env
    print_success "Archivo .env creado desde .env.example"
    print_warning "Por favor edita config/.env con tus API keys"
else
    print_warning "Archivo .env ya existe"
fi

# Test de data collector
echo ""
echo "8. Probando data collector..."
python3 << EOF
import sys
sys.path.append('src')
from data.data_collector import DataCollector

try:
    collector = DataCollector('binance', sandbox=True)
    print("✓ Data collector inicializado correctamente")
except Exception as e:
    print(f"✗ Error en data collector: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Data collector funcionando"
else
    print_error "Error en data collector"
fi

# Test de base de datos
echo ""
echo "9. Probando base de datos..."
python3 << EOF
import sys
sys.path.append('src')
from utils.database import TradingDatabase

try:
    db = TradingDatabase('data/trading.db')
    print("✓ Base de datos inicializada correctamente")
except Exception as e:
    print(f"✗ Error en base de datos: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Base de datos funcionando"
else
    print_error "Error en base de datos"
fi

# Test de backup manager
echo ""
echo "10. Probando sistema de backups..."
python3 << EOF
import sys
sys.path.append('src')
from utils.backup_manager import BackupManager
from pathlib import Path

try:
    project_root = Path('.').resolve()
    backup_manager = BackupManager(str(project_root), 'backups', retention_days=7)
    print("✓ Backup manager inicializado correctamente")
except Exception as e:
    print(f"✗ Error en backup manager: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Backup manager funcionando"
else
    print_error "Error en backup manager"
fi

# Resumen
echo ""
echo "========================================="
echo "Resumen de Instalación"
echo "========================================="
print_success "Python: $PYTHON_VERSION"
print_success "Entorno virtual: venv/"
print_success "Dependencias: Instaladas"
print_success "Directorios: Creados"
print_success "Data collector: Funcionando"
print_success "Base de datos: Funcionando"
print_success "Backup manager: Funcionando"
echo ""
print_warning "Próximos pasos:"
echo "  1. Edita config/.env con tus API keys"
echo "  2. Ejecuta: python src/data/data_collector.py (test de descarga)"
echo "  3. Revisa docs/fase1_documentacion.md para más detalles"
echo ""
print_success "¡Instalación completada!"
echo ""
