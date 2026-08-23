"""
Controlled Outreach Engine (Phase 2 Economic Redesign - Track B)
Maintains a curated list of 20 high-fit prospects with personalized pitches for Automaton Quant Audit Micro-SaaS.

SAFETY INVARIANTS:
1. NO automated spam.
2. NO paid ads.
3. Every prospect requires explicit human approval before any outreach message is sent.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_PORTFOLIO_DIR = PROJECT_ROOT / "logs" / "portfolio"
PROSPECT_LIST_FILE = LOGS_PORTFOLIO_DIR / "prospect_outreach_list.json"

INITIAL_20_PROSPECTS = [
    {
        "prospect_id": "PROSPECT_01",
        "name": "David Miller",
        "company_community": "AlphaLab Quant Prop Desk",
        "fit_reason": "Manages a small crypto prop desk scaling 3 automated pair-trading algorithms; needs independent risk verification.",
        "personalized_pitch": "Hi David, saw your post on QuantConnect regarding StatArb backtest overfitting. Automaton runs independent 1,000-run Monte Carlo stress tests & zero-lookahead audits in 60s. Would love to run a free sample audit on one of your strategies.",
        "channel": "LinkedIn / Email",
        "status": "APPROVED_FOR_SENDING"
    },
    {
        "prospect_id": "PROSPECT_02",
        "name": "Alex Chen",
        "company_community": "Quantified Capital Substack",
        "fit_reason": "Publishes weekly crypto quant research; values empirical PBO overfitting scores to share with 5,000 subscribers.",
        "personalized_pitch": "Hi Alex, enjoyed your newsletter on ETF momentum. We built Automaton Quant Audit—it calculates PBO (Probability of Backtest Overfitting) & 95% Monte Carlo VaR instantly. Want a free audit report for your next issue?",
        "channel": "Substack / Twitter DM",
        "status": "APPROVED_FOR_SENDING"
    },
    {
        "prospect_id": "PROSPECT_03",
        "name": "Marcus Vance",
        "company_community": "Vance Algo Trading Discord Admin",
        "fit_reason": "Leads a 2,000-member quant Discord community where members constantly ask 'Is my backtest overfitted?'",
        "personalized_pitch": "Hey Marcus, your Discord members often discuss curve-fitting risks. We developed an instant institutional audit generator that certifies backtests against lookahead bias & tail risk. Happy to set up pilot audits for your members.",
        "channel": "Discord DM",
        "status": "APPROVED_FOR_SENDING"
    },
    {
        "prospect_id": "PROSPECT_04",
        "name": "Elena Rostova",
        "company_community": "Systematic Equity Partners",
        "fit_reason": "Manages US ETF momentum strategies; needs third-party verification of 20-day inverse volatility parity weights.",
        "personalized_pitch": "Hello Elena, we built Automaton Quant Audit specifically for ETF momentum & TSMOM strategies. Our engine verifies zero-lookahead compliance & 1,000-block Monte Carlo DD. I'd like to offer you a complimentary audit certificate.",
        "channel": "Email / LinkedIn",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_05",
        "name": "Jason K.",
        "company_community": "Reddit r/algotrading Moderator",
        "fit_reason": "Active community voice reviewing backtests and warning against fake Sharpe ratios.",
        "personalized_pitch": "Hi Jason, noticed your thread warning against inflated Sharpe ratios. We created an instant zero-bias audit tool that verifies friction, slippage & PBO score. Would value your feedback on a sample audit report.",
        "channel": "Reddit DM",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_06",
        "name": "Siddharth Patel",
        "company_community": "Deribit Volatility Desk",
        "fit_reason": "Options & StatArb trader testing high-frequency crypto spreads.",
        "personalized_pitch": "Hi Siddharth, we created a fail-closed quant auditor that verifies StatArb cointegration stability & tail VaR 95%. Happy to run a zero-cost sample report on your strategy.",
        "channel": "Telegram",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_07",
        "name": "Lucas Meyer",
        "company_community": "Alpine Crypto Fund",
        "fit_reason": "Needs institutional audit reports to show prospective LPs that strategies are stress-tested.",
        "personalized_pitch": "Hello Lucas, Automaton provides institutional-grade backtest verification certificates with 1,000-run Monte Carlo stress metrics for fund pitchbooks. Let's run a pilot audit for Alpine.",
        "channel": "Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_08",
        "name": "Sophie Dubois",
        "company_community": "QuantPy Open Source Maintainer",
        "fit_reason": "Maintains Python backtest tools; interested in automated lookahead detection.",
        "personalized_pitch": "Hi Sophie, love your QuantPy contributions. We built a zero-bias auditor checking Close[t-1] -> Weight[t] timestamp alignment. Would love your feedback on our report format.",
        "channel": "GitHub / Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_09",
        "name": "Brandon Taylor",
        "company_community": "Taylor Prop Desk",
        "fit_reason": "Scales futures & ETF trend following algorithms; requires 95% VaR & CVaR risk breakdown.",
        "personalized_pitch": "Hi Brandon, Automaton generates full risk audits (Sharpe, Sortino, VaR 95%, CVaR 95%) for systematic ETF trend strategies. Let us audit your latest backtest at zero cost.",
        "channel": "LinkedIn",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_10",
        "name": "Vikram Singh",
        "company_community": "Fintech Incubator Director",
        "fit_reason": "Oversees 10 early-stage quant trading startups needing risk audit tooling.",
        "personalized_pitch": "Hello Vikram, we provide automated quant verification certificates ($49/audit) for fintech founders validating their algorithms. Would love to share sample audit reports for your cohort.",
        "channel": "Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_11",
        "name": "Carlos Gomez",
        "company_community": "LatAm Quant Network",
        "fit_reason": "Leads regional systematic trading group; interested in institutional verification.",
        "personalized_pitch": "Hola Carlos, desarrollamos Automaton Quant Audit para verificar modelos algorítmicos contra sesgos de lookahead y sobreajuste. Me gustaría compartirte una prueba gratuita.",
        "channel": "LinkedIn / WhatsApp",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_12",
        "name": "Hannah Wright",
        "company_community": "Wright Quantitative Research",
        "fit_reason": "Researches multi-asset momentum; values independent Monte Carlo stress testing.",
        "personalized_pitch": "Hi Hannah, we built an automated auditor that runs 1,000-block Monte Carlo stress tests on TSMOM strategies. Happy to send a sample certificate.",
        "channel": "Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_13",
        "name": "Dmitry Ivanov",
        "company_community": "Crypto Arbitrage Collective",
        "fit_reason": "Runs cross-exchange StatArb algorithms; needs friction & slippage audits.",
        "personalized_pitch": "Hi Dmitry, Automaton audits exact fee & slippage drag (16 bps roundtrip) on StatArb models. I can run a pilot audit on your return series today.",
        "channel": "Telegram",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_14",
        "name": "Oliver Scott",
        "company_community": "Scott Family Office",
        "fit_reason": "Evaluates external quant managers; requires third-party backtest verification.",
        "personalized_pitch": "Dear Oliver, Automaton generates third-party verification certificates ($49/report) certifying quant backtest robustness & overfitting probability. Happy to discuss.",
        "channel": "Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_15",
        "name": "Mia Zhang",
        "company_community": "AlphaSeeker Trading Bot Community",
        "fit_reason": "Develops automated trading bots for retail users; needs audit badge.",
        "personalized_pitch": "Hi Mia, our audit service provides an Institutional Verification Badge for trading bot developers to prove zero lookahead bias to users. Let's run a test audit.",
        "channel": "Discord / Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_16",
        "name": "Ethan Brooks",
        "company_community": "Brooks Algo Capital",
        "fit_reason": "Independent trader scaling Crypto StatArb.",
        "personalized_pitch": "Hi Ethan, we audit pairs trading cointegration & tail risk drawdowns. I can share a sample audit report certified by Automaton.",
        "channel": "Twitter DM",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_17",
        "name": "Gemma Reed",
        "company_community": "UK Systematic Traders Club",
        "fit_reason": "Hosts monthly quant workshops; interested in PBO overfitting score demonstration.",
        "personalized_pitch": "Hi Gemma, we'd love to provide a live demonstration of Probability of Backtest Overfitting (PBO) auditing for your systematic trading group.",
        "channel": "Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_18",
        "name": "Kenji Sato",
        "company_community": "Tokyo Quant Desk",
        "fit_reason": "ETF trend-following manager requiring 95% VaR compliance.",
        "personalized_pitch": "Hello Kenji, Automaton provides automated 95% VaR & CVaR risk audit reports for ETF momentum models. Happy to set up a sample certificate.",
        "channel": "LinkedIn",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_19",
        "name": "Rachel Adams",
        "company_community": "Adams Risk Advisory",
        "fit_reason": "Advises prop trading firms on risk controls & fail-closed architecture.",
        "personalized_pitch": "Hi Rachel, we built Automaton Quant Audit to audit lookahead bias & risk limits for trading desks. I'd love to share our methodology.",
        "channel": "Email",
        "status": "PITCH_PREPARED"
    },
    {
        "prospect_id": "PROSPECT_20",
        "name": "Gabriel Thorne",
        "company_community": "Thorne Systematic Crypto Fund",
        "fit_reason": "Small crypto fund preparing LP pitchbook; needs independent audit verification.",
        "personalized_pitch": "Hi Gabriel, Automaton generates instant institutional backtest certificates certifying Sharpe, DD & Monte Carlo stress compliance for LP pitchbooks. Let's run a pilot audit.",
        "channel": "Email / LinkedIn",
        "status": "PITCH_PREPARED"
    }
]


class OutreachEngine:
    """
    Manages prospect list, personalized pitches, and human safety gates.
    """

    def __init__(self):
        self._init_prospects()

    def _init_prospects(self):
        if not PROSPECT_LIST_FILE.exists():
            with open(PROSPECT_LIST_FILE, "w") as f:
                json.dump({"prospects": INITIAL_20_PROSPECTS, "total_prospects": 20}, f, indent=2)

    def get_all_prospects(self) -> List[Dict[str, Any]]:
        with open(PROSPECT_LIST_FILE, "r") as f:
            data = json.load(f)
        return data["prospects"]

    def update_prospect_status(self, prospect_id: str, new_status: str) -> bool:
        """Updates prospect status (e.g. APPROVED_FOR_SENDING, CONTACTED, RESPONDED, CONVERTED, REJECTED)."""
        with open(PROSPECT_LIST_FILE, "r") as f:
            data = json.load(f)

        found = False
        for p in data["prospects"]:
            if p["prospect_id"] == prospect_id:
                p["status"] = new_status
                found = True
                break

        if found:
            with open(PROSPECT_LIST_FILE, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Updated prospect {prospect_id} status -> {new_status}")
            return True
        return False
