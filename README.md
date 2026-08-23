# Autonomous Trading System

**Objetivo:** Sistema de trading autónomo con agentes AI para generar ingresos constantes y escalables.

## Hardware Actual
- MacBook Air M2 (8GB RAM, 100GB HD)
- Plan: Migrar a Nvidia DGX Spark cuando esté disponible

## Fase Actual: Fase 1.5 - Backtesting y Estrategias Implementadas

### Estructura del Proyecto
```
trading-autonomous-system/
├── src/
│   ├── data/           # Scripts de recolección de datos
│   ├── strategies/     # Implementación de estrategias
│   ├── backtesting/    # Motor de backtesting
│   └── utils/          # Utilidades compartidas
├── docs/
│   ├── architecture/   # Documentación arquitectónica
│   └── research/       # Investigación de estrategias
├── config/             # Configuraciones
├── logs/               # Logs del sistema
├── backups/            # Respaldos automatizados
├── data/
│   ├── raw/            # Datos crudos
│   └── processed/      # Datos procesados
└── notebooks/          # Jupyter notebooks para análisis
```

## Progreso

### Fase 1: Infraestructura de Datos y Backtesting (Sin IA)
- [x] Estructura del proyecto
- [x] Sistema de data collection
- [x] Sistema de base de datos SQLite
- [x] Sistema de respaldos automatizados
- [x] Backtesting engine determinista
- [x] Indicadores técnicos básicos

### Fase 1.5: Backtesting y Estrategias (Sin IA)
- [x] Motor de backtesting completo
- [x] Estrategia Grid Trading implementada
- [x] Sistema de métricas de performance
- [x] Script de ejecución de backtests
- [x] Validación con datos de prueba

### Fase 2: Modelos Ligeros en M2 (Ollama)
- [ ] Instalar Ollama con modelos optimizados
- [ ] Prototipado de skills y prompts

### Fase 3: Estrategias Sin IA (Matemáticas Puras)
- [ ] Funding Rate Arbitrage
- [ ] Statistical Arbitrage
- [ ] Grid Trading

### Fase 4: Dashboard de Monitoreo
- [ ] Dashboard con Streamlit/Dash

### Fase 5: APIs Cloud para IA Pesada (Opcional)
- [ ] Integración con APIs cloud

### Fase 6: Preparación para Migración a DGX Spark
- [ ] Documentación completa
- [ ] Pipeline de datos listo
- [ ] Estrategias validadas

## Metodología

Este proyecto sigue el **Método Karpathy**:
1. Implementación más simple posible primero
2. Verificación constante de cada componente
3. Iteración basada en datos reales
4. Escalado solo cuando es necesario

## Responsables

- Desarrollador: Jorge Atilano
- Asistente AI: Devin
