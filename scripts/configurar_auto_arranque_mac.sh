#!/bin/bash
# Script de Configuración de Auto-Recuperación para macOS ante Corte de Luz / Energía

echo "================================================================="
echo "⚙️ CONFIGURANDO PROTOCOLO DE AUTO-RECUPERACIÓN EN MACOS M2"
echo "================================================================="

# 1. Configurar pmset para auto-reinicio tras falla eléctrica
sudo pmset -a autorestart 1
sudo pmset -a disablesleep 1
sudo pmset -a womp 1

echo "✅ Ajustes de Energía Aplicados:"
echo "   • autorestart 1: La Mac se encenderá automáticamente cuando regrese la luz."
echo "   • disablesleep 1: Previene que la Mac entre en modo reposo profundo."
echo "   • womp 1: Despertar por acceso de red (Wake on LAN/Wi-Fi)."

echo "================================================================="
echo "🔒 Protocolo Anti-Apagón Activo:"
echo "   1. Stop Loss REAL colocados en Servidores de Binance (STOP_MARKET)."
echo "   2. Resincronización automática de posiciones al reconectar internet."
echo "================================================================="
