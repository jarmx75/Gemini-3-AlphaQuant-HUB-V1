"""
Paper Gate Progress Monitor (Operational)
Rastrea el progreso forward hacia los 100 paper trades cerrados por estrategia,
mide el solapamiento del portafolio (portfolio overlap) y detecta anomalías operativas.

REGLAS ESTRICTAS DE SEGURIDAD:
- APPROVED = false
- DEMO_ORDERS = 0
- REAL_ORDERS = 0
- PAPER_GATE_READY únicamente cuando closed_paper_trades >= 100.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

REGISTRY_PATH = PROJECT_ROOT / "src" / "factory" / "registry.json"
PAPER_LOG_CSV = PROJECT_ROOT / "logs" / "paper" / "bitacora_pairs_trading_paper.csv"
RUNNER_HEALTH_JSON = PROJECT_ROOT / "logs" / "paper" / "runner_health.json"
OUTPUT_DIR = PROJECT_ROOT / "logs" / "execution"
OUTPUT_JSON = OUTPUT_DIR / "paper_gate_progress.json"
OUTPUT_MD = PROJECT_ROOT / "docs" / "PAPER_GATE_PROGRESS.md"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class PaperGateMonitor:
    """Monitor operativo de progreso del Paper Gate hacia 100 trades."""

    def __init__(
        self,
        registry_path: Optional[Path] = None,
        bitacora_path: Optional[Path] = None,
        runner_health_path: Optional[Path] = None,
        output_json_path: Optional[Path] = None,
        output_md_path: Optional[Path] = None,
        initial_capital: float = 5000.0,
        gate_target_trades: int = 100
    ):
        self.registry_path = Path(registry_path or REGISTRY_PATH)
        self.bitacora_path = Path(bitacora_path or PAPER_LOG_CSV)
        self.runner_health_path = Path(runner_health_path or RUNNER_HEALTH_JSON)
        self.output_json_path = Path(output_json_path or OUTPUT_JSON)
        self.output_md_path = Path(output_md_path or OUTPUT_MD)
        self.initial_capital = initial_capital
        self.gate_target = gate_target_trades

        # Expected historical frequencies per month (from Reconciliation Audit)
        self.historical_expected_rate = {
            "Pairs_Stat_Arb_Base": 9.69,
            "Pairs_W90_Z2.5_S3.5_H24": 9.69,
            "Pairs_W90_Z2.4_S3.5_H24": 10.13
        }

    def load_active_strategies(self) -> List[Dict[str, Any]]:
        """Lee registry.json y extrae solo las estrategias con status PAPER_ACTIVE."""
        if not self.registry_path.exists():
            logger.warning(f"Registry file not found: {self.registry_path}")
            return []
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [s for s in data.get("active_paper_strategies", []) if s.get("status") == "PAPER_ACTIVE"]
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return []

    def load_paper_bitacora(self) -> pd.DataFrame:
        """Carga la bitácora de paper trading y filtra filas válidas."""
        if not self.bitacora_path.exists() or self.bitacora_path.stat().st_size == 0:
            return pd.DataFrame()
        try:
            df = pd.read_csv(self.bitacora_path)
            if df.empty or 'strategy_id' not in df.columns:
                return pd.DataFrame()
            return df
        except Exception as e:
            logger.error(f"Error loading bitacora: {e}")
            return pd.DataFrame()

    def load_runner_health(self) -> Dict[str, Any]:
        """Carga el estado de salud del runner."""
        if not self.runner_health_path.exists():
            return {}
        try:
            with open(self.runner_health_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading runner health: {e}")
            return {}

    def compute_strategy_metrics(
        self,
        strategy_id: str,
        df_strat_closed: pd.DataFrame,
        health_info: Dict[str, Any],
        promoted_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calcula métricas individuales y evalúa el Paper Gate para una estrategia."""
        closed_trades_count = len(df_strat_closed)
        progress_pct = round((closed_trades_count / float(self.gate_target)) * 100.0, 2)
        remaining_trades = max(0, self.gate_target - closed_trades_count)

        # Calculate time running
        now_dt = datetime.now(timezone.utc)
        start_dt = None
        if promoted_at:
            try:
                start_dt = datetime.fromisoformat(promoted_at.replace("Z", "+00:00"))
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
            except Exception:
                start_dt = None

        if start_dt:
            days_running = max(0.01, round((now_dt - start_dt).total_seconds() / 86400.0, 2))
        else:
            days_running = 0.01

        # Metrics calculation
        if closed_trades_count == 0:
            pnl_total = 0.0
            win_rate = 0.0
            pf = 0.0
            max_dd = 0.0
            max_loss_streak = 0
            avg_trade = 0.0
            avg_holding = 0.0
            avg_fee = 0.0
            first_trade = None
            last_trade = None
            estimated_days_to_100 = "INSUFFICIENT_FORWARD_DATA"
        else:
            pnl_col = 'pnl' if 'pnl' in df_strat_closed.columns else 'net_pnl'
            df_strat_closed[pnl_col] = pd.to_numeric(df_strat_closed[pnl_col], errors='coerce').fillna(0.0)
            pnl_series = df_strat_closed[pnl_col]
            
            pnl_total = round(float(pnl_series.sum()), 2)
            wins = df_strat_closed[pnl_series > 0]
            losses = df_strat_closed[pnl_series <= 0]
            
            win_rate = round((len(wins) / closed_trades_count) * 100.0, 2)
            gw = float(wins[pnl_col].sum()) if not wins.empty else 0.0
            gl = abs(float(losses[pnl_col].sum())) if not losses.empty else 0.0
            pf = round(gw / gl, 2) if gl > 0 else (99.0 if gw > 0 else 0.0)
            
            # Max DD
            equity = self.initial_capital + pnl_series.cumsum()
            peak = equity.cummax()
            dd_pct = ((peak - equity) / peak) * 100.0
            max_dd = round(float(dd_pct.max()), 2)
            
            # Loss streak
            max_loss_streak = 0
            current_streak = 0
            for val in pnl_series:
                if val <= 0:
                    current_streak += 1
                    if current_streak > max_loss_streak:
                        max_loss_streak = current_streak
                else:
                    current_streak = 0
                    
            avg_trade = round(pnl_total / closed_trades_count, 2)
            
            # Holding bars
            if 'holding_bars' in df_strat_closed.columns:
                avg_holding = round(float(pd.to_numeric(df_strat_closed['holding_bars'], errors='coerce').fillna(0).mean()), 1)
            else:
                avg_holding = 0.0
                
            # Fees
            if 'fees' in df_strat_closed.columns:
                avg_fee = round(float(pd.to_numeric(df_strat_closed['fees'], errors='coerce').fillna(0).mean()), 4)
            else:
                avg_fee = 0.0

            first_trade = str(df_strat_closed.iloc[0]['timestamp']) if 'timestamp' in df_strat_closed.columns else None
            last_trade = str(df_strat_closed.iloc[-1]['timestamp']) if 'timestamp' in df_strat_closed.columns else None

            # Estimated days using ONLY forward paper frequency
            forward_rate_per_day = closed_trades_count / days_running
            if forward_rate_per_day > 0 and remaining_trades > 0:
                estimated_days_to_100 = round(remaining_trades / forward_rate_per_day, 1)
            elif remaining_trades == 0:
                estimated_days_to_100 = 0.0
            else:
                estimated_days_to_100 = "INSUFFICIENT_FORWARD_DATA"

        # Runner health details
        last_sig = health_info.get("last_signal_by_strategy", {}).get(strategy_id)
        runner_status = health_info.get("status", "UNKNOWN")

        # Gate status determination
        if closed_trades_count >= self.gate_target:
            gate_status = "PAPER_GATE_READY"
        elif "RUNNING" in runner_status:
            gate_status = "PAPER_ACTIVE"
        else:
            gate_status = "PAPER_GATE_PENDING"

        # Anomaly Detection
        anomalies = []
        if closed_trades_count >= 20 and pf < 0.80:
            anomalies.append(f"WARN: PF_DEGRADATION (PF={pf:.2f} < 0.80 after {closed_trades_count} trades)")
        if max_dd > 15.0:
            anomalies.append(f"WARN: EXCESSIVE_DRAWDOWN (Max DD={max_dd:.1f}% > 15.0%)")
        if avg_fee > 0.50:  # Nominal threshold based on $300 notional * 0.08% = $0.24
            anomalies.append(f"WARN: EXCESSIVE_FEES (Avg Fee=${avg_fee:.2f} > backtest assumption)")
        
        # Frequency collapse check (if running >= 14 days and rate < 50% historical)
        if days_running >= 14.0 and closed_trades_count > 0:
            actual_monthly_rate = (closed_trades_count / days_running) * 30.0
            expected_rate = self.historical_expected_rate.get(strategy_id, 9.7)
            if actual_monthly_rate < (expected_rate * 0.5):
                anomalies.append(
                    f"WARN: FREQUENCY_COLLAPSE (Forward rate {actual_monthly_rate:.1f}/mo < 50% of expected {expected_rate:.1f}/mo)"
                )

        return {
            "strategy_id": strategy_id,
            "closed_paper_trades": closed_trades_count,
            "progress_pct": progress_pct,
            "remaining_trades": remaining_trades,
            "first_paper_trade": first_trade,
            "last_paper_trade": last_trade,
            "paper_PnL": pnl_total,
            "paper_win_rate": win_rate,
            "paper_PF": pf,
            "paper_DD": max_dd,
            "max_loss_streak": max_loss_streak,
            "avg_trade": avg_trade,
            "avg_holding_time_bars": avg_holding,
            "last_signal": last_sig,
            "days_running": days_running,
            "estimated_days_to_100": estimated_days_to_100,
            "gate_status": gate_status,
            "anomaly_flags": anomalies
        }

    def compute_portfolio_overlap(self, df_bitacora: pd.DataFrame) -> Dict[str, Any]:
        """Calcula el solapamiento de trades/posiciones entre las 3 estrategias."""
        overlap_report = {
            "overlap_Base_vs_Z2.5": {"concurrent_trades": 0, "overlap_pct": 0.0},
            "overlap_Base_vs_Z2.4": {"concurrent_trades": 0, "overlap_pct": 0.0},
            "overlap_Z2.5_vs_Z2.4": {"concurrent_trades": 0, "overlap_pct": 0.0},
            "total_open_trades_logged": len(df_bitacora[df_bitacora['action'] == 'OPEN']) if not df_bitacora.empty and 'action' in df_bitacora.columns else 0,
            "total_closed_trades_logged": len(df_bitacora[df_bitacora['action'] == 'CLOSE']) if not df_bitacora.empty and 'action' in df_bitacora.columns else 0,
            "notes": "Report-only metric. Does not block execution."
        }

        if df_bitacora.empty or 'position_id' not in df_bitacora.columns or 'action' not in df_bitacora.columns:
            return overlap_report

        # Analyze positions by timestamp & pair
        df_opens = df_bitacora[df_bitacora['action'] == 'OPEN'].copy()
        if df_opens.empty:
            return overlap_report

        # Group by timestamp and pair to find simultaneous entries
        grouped = df_opens.groupby(['timestamp', 'pair'])['strategy_id'].apply(list).reset_index()

        base_id = "Pairs_Stat_Arb_Base"
        z25_id = "Pairs_W90_Z2.5_S3.5_H24"
        z24_id = "Pairs_W90_Z2.4_S3.5_H24"

        c_base_z25 = 0
        c_base_z24 = 0
        c_z25_z24 = 0

        for strats in grouped['strategy_id']:
            s_set = set(strats)
            if base_id in s_set and z25_id in s_set:
                c_base_z25 += 1
            if base_id in s_set and z24_id in s_set:
                c_base_z24 += 1
            if z25_id in s_set and z24_id in s_set:
                c_z25_z24 += 1

        total_groups = max(1, len(grouped))
        overlap_report["overlap_Base_vs_Z2.5"] = {
            "concurrent_trades": c_base_z25,
            "overlap_pct": round((c_base_z25 / total_groups) * 100.0, 2)
        }
        overlap_report["overlap_Base_vs_Z2.4"] = {
            "concurrent_trades": c_base_z24,
            "overlap_pct": round((c_base_z24 / total_groups) * 100.0, 2)
        }
        overlap_report["overlap_Z2.5_vs_Z2.4"] = {
            "concurrent_trades": c_z25_z24,
            "overlap_pct": round((c_z25_z24 / total_groups) * 100.0, 2)
        }

        return overlap_report

    def run_monitor(self) -> Dict[str, Any]:
        """Ejecuta el ciclo completo del monitor y persiste los reportes."""
        active_strategies = self.load_active_strategies()
        df_bitacora = self.load_paper_bitacora()
        health_info = self.load_runner_health()

        valid_strategy_ids = {s['id'] for s in active_strategies}

        # Filter bitacora for closed trades of active strategies only
        if not df_bitacora.empty and 'action' in df_bitacora.columns and 'strategy_id' in df_bitacora.columns:
            df_closed_all = df_bitacora[
                (df_bitacora['action'] == 'CLOSE') & (df_bitacora['strategy_id'].isin(valid_strategy_ids))
            ].copy()
        else:
            df_closed_all = pd.DataFrame()

        strategy_progress = []
        all_gate_ready = True if active_strategies else False

        for strat in active_strategies:
            strat_id = strat['id']
            promoted_at = strat.get('promoted_at')
            if not df_closed_all.empty:
                df_strat_closed = df_closed_all[df_closed_all['strategy_id'] == strat_id].copy()
            else:
                df_strat_closed = pd.DataFrame()

            metrics = self.compute_strategy_metrics(strat_id, df_strat_closed, health_info, promoted_at)
            strategy_progress.append(metrics)

            if metrics['gate_status'] != "PAPER_GATE_READY":
                all_gate_ready = False

        portfolio_overlap = self.compute_portfolio_overlap(df_bitacora)

        overall_status = "ALL_PAPER_GATE_READY" if all_gate_ready else "PAPER_GATE_IN_PROGRESS"

        report = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "overall_status": overall_status,
            "paper_gate_target_trades": self.gate_target,
            "active_strategies_count": len(active_strategies),
            "strategies_progress": strategy_progress,
            "portfolio_overlap": portfolio_overlap,
            "security_invariants": {
                "APPROVED": False,
                "DEMO_ORDERS": 0,
                "REAL_ORDERS": 0,
                "human_approval": "PENDING"
            }
        }

        # Ensure directories exist
        self.output_json_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_md_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        self._generate_markdown_report(report)
        logger.info(f"✅ Paper gate progress saved to {self.output_json_path} and {self.output_md_path}")
        return report

    def _generate_markdown_report(self, report: Dict[str, Any]):
        """Genera el documento Markdown de seguimiento del Paper Gate."""
        md = f"""# Monitor de Progreso del Paper Gate (100 Trades Forward)

**Última Actualización**: `{report['timestamp']}`  
**Estado General del Gate**: `{report['overall_status']}`  
**Objetivo de Seguridad**: Requerimiento estricto de **{report['paper_gate_target_trades']} trades cerrados** en forward paper antes de evaluar Binance Demo.  
**Invariantes de Seguridad**: `APPROVED=false` | `DEMO_ORDERS=0` | `REAL_ORDERS=0`

---

## 1. Tabla de Progreso por Estrategia

| Estrategia ID | Trades Cerrados | Progreso (%) | Restantes | Win Rate (%) | PnL Paper | PF Paper | Max DD (%) | Días Activo | Est. Días a 100 | Estado del Gate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
        for sp in report["strategies_progress"]:
            est_days = sp['estimated_days_to_100']
            est_str = f"{est_days} d" if isinstance(est_days, (int, float)) else str(est_days)
            md += (
                f"| `{sp['strategy_id']}` | **{sp['closed_paper_trades']} / {self.gate_target}** | "
                f"**{sp['progress_pct']}%** | {sp['remaining_trades']} | {sp['paper_win_rate']}% | "
                f"${sp['paper_PnL']:.2f} | {sp['paper_PF']:.2f} | {sp['paper_DD']:.1f}% | "
                f"{sp['days_running']} | {est_str} | `{sp['gate_status']}` |\n"
            )

        md += """
---

## 2. Detalle de Señales y Operativa

"""
        for sp in report["strategies_progress"]:
            sig_info = sp['last_signal'] if sp['last_signal'] else "Ninguna señal registrada aún"
            anomalies = sp['anomaly_flags']
            anomaly_str = " | ".join(anomalies) if anomalies else "✅ Normal (Sin anomalías)"

            md += f"""### 📌 `{sp['strategy_id']}`
- **Primer Trade Paper**: `{sp['first_paper_trade'] or 'N/A'}`
- **Último Trade Paper**: `{sp['last_paper_trade'] or 'N/A'}`
- **Promedio por Trade**: `${sp['avg_trade']:.2f} USD`
- **Holding Promedio**: `{sp['avg_holding_time_bars']} barras`
- **Racha Máxima de Pérdidas**: `{sp['max_loss_streak']} trades`
- **Última Señal**: `{sig_info}`
- **Alertas / Anomalías**: `{anomaly_str}`

"""

        md += f"""---

## 3. Análisis de Solapamiento del Portafolio (Portfolio Overlap)

| Par de Estrategias | Entradas Simultáneas | % de Solapamiento | Estado Operativo |
| :--- | :---: | :---: | :---: |
| `Base` vs `W90_Z2.5_S3.5_H24` | **{report['portfolio_overlap']['overlap_Base_vs_Z2.5']['concurrent_trades']}** | **{report['portfolio_overlap']['overlap_Base_vs_Z2.5']['overlap_pct']}%** | ℹ️ Supervisión Continua |
| `Base` vs `W90_Z2.4_S3.5_H24` | **{report['portfolio_overlap']['overlap_Base_vs_Z2.4']['concurrent_trades']}** | **{report['portfolio_overlap']['overlap_Base_vs_Z2.4']['overlap_pct']}%** | ℹ️ Supervisión Continua |
| `W90_Z2.5` vs `W90_Z2.4` | **{report['portfolio_overlap']['overlap_Z2.5_vs_Z2.4']['concurrent_trades']}** | **{report['portfolio_overlap']['overlap_Z2.5_vs_Z2.4']['overlap_pct']}%** | ℹ️ Supervisión Continua |

> [!NOTE]
> El solapamiento es una métrica de monitoreo e información. **No bloquea la ejecución** de las estrategias ni altera los parámetros configurados.

---

## 4. Reglas del Paper Gate y Criterios de Promoción

1. **Requisito Cuantitativo**: Cada estrategia debe acumular de forma independiente $\\ge 100$ trades cerrados en forward paper mode (`gate_status == 'PAPER_GATE_READY'`).
2. **Requisito Cualitativo**:
   - $\\text{{PF Paper}} \\ge 1.20$
   - $\\text{{Max DD Paper}} < 12.0\\%$
   - Ausencia de anomalías de ejecución (`SLIPPAGE_BREACH`, `EXCESSIVE_FEES`).
3. **Cero Bypass**:
   - `OPEN` trades no cuentan hacia el umbral de 100.
   - Backtests históricos no cuentan hacia el umbral de 100.
   - `APPROVED` requiere firma manual humana explícita posterior a la aprobación del Paper Gate.
"""
        with open(self.output_md_path, "w", encoding="utf-8") as f:
            f.write(md)


if __name__ == '__main__':
    monitor = PaperGateMonitor()
    monitor.run_monitor()
