"""
Position Manager Module
Tracks multi-strategy positions, exposure calculations, leverage compliance,
and position lifecycle transitions.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PositionLeg:
    symbol: str
    side: str  # 'BUY' (Long) or 'SELL' (Short)
    quantity: float
    entry_price: float
    current_price: float = 0.0
    leverage: int = 10
    notional: float = 0.0


@dataclass
class StrategyPosition:
    position_id: str
    strategy_id: str
    pair_name: str
    side: str  # 'LONG_SPREAD' or 'SHORT_SPREAD'
    leg_y: PositionLeg
    leg_x: PositionLeg
    gamma: float
    entry_time: str
    entry_timestamp: int
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    accumulated_funding: float = 0.0
    accumulated_fees: float = 0.0
    is_open: bool = True
    close_time: Optional[str] = None
    close_reason: Optional[str] = None


class PositionManager:
    """
    Tracks local state of all open and historical strategy positions.
    """

    def __init__(self, max_concurrent_positions: int = 3, notional_per_leg: float = 150.0):
        self.max_concurrent_positions = max_concurrent_positions
        self.notional_per_leg = notional_per_leg
        self.open_positions: Dict[str, StrategyPosition] = {}  # key: position_id or pair_name
        self.closed_positions: List[StrategyPosition] = []

    def can_open_position(self, strategy_id: str) -> bool:
        """Checks if new position is permitted within portfolio limits."""
        if len(self.open_positions) >= self.max_concurrent_positions:
            logger.warning(f"Position limit reached: {len(self.open_positions)}/{self.max_concurrent_positions}")
            return False
        return True

    def open_pair_position(
        self,
        strategy_id: str,
        pair_name: str,
        side: str,
        sym_y: str,
        side_y: str,
        qty_y: float,
        price_y: float,
        sym_x: str,
        side_x: str,
        qty_x: float,
        price_x: float,
        gamma: float,
        entry_time_str: str,
        leverage: int = 10
    ) -> StrategyPosition:
        """Opens a local paired position."""
        pos_id = f"{strategy_id}_{pair_name}_{int(time.time())}"
        
        leg_y = PositionLeg(
            symbol=sym_y,
            side=side_y,
            quantity=qty_y,
            entry_price=price_y,
            current_price=price_y,
            leverage=leverage,
            notional=qty_y * price_y
        )
        leg_x = PositionLeg(
            symbol=sym_x,
            side=side_x,
            quantity=qty_x,
            entry_price=price_x,
            current_price=price_x,
            leverage=leverage,
            notional=qty_x * price_x
        )

        pos = StrategyPosition(
            position_id=pos_id,
            strategy_id=strategy_id,
            pair_name=pair_name,
            side=side,
            leg_y=leg_y,
            leg_x=leg_x,
            gamma=gamma,
            entry_time=entry_time_str,
            entry_timestamp=int(time.time()),
            is_open=True
        )

        self.open_positions[pair_name] = pos
        logger.info(f"📊 [POSITION OPENED] {pair_name} ({side}) | Leg Y: {side_y} {qty_y} {sym_y} @ {price_y} | Leg X: {side_x} {qty_x} {sym_x} @ {price_x}")
        return pos

    def close_pair_position(
        self,
        pair_name: str,
        exit_price_y: float,
        exit_price_x: float,
        close_time_str: str,
        close_reason: str,
        fees: float = 0.0
    ) -> Optional[StrategyPosition]:
        """Closes an open position and calculates realized PnL."""
        if pair_name not in self.open_positions:
            logger.warning(f"Attempted to close nonexistent position for pair {pair_name}")
            return None

        pos = self.open_positions.pop(pair_name)
        pos.is_open = False
        pos.close_time = close_time_str
        pos.close_reason = close_reason
        pos.accumulated_fees = fees

        # Calculate PnL for leg Y
        if pos.leg_y.side == 'BUY':
            pnl_y = (exit_price_y - pos.leg_y.entry_price) * pos.leg_y.quantity
        else:
            pnl_y = (pos.leg_y.entry_price - exit_price_y) * pos.leg_y.quantity

        # Calculate PnL for leg X
        if pos.leg_x.side == 'BUY':
            pnl_x = (exit_price_x - pos.leg_x.entry_price) * pos.leg_x.quantity
        else:
            pnl_x = (pos.leg_x.entry_price - exit_price_x) * pos.leg_x.quantity

        pos.realized_pnl = (pnl_y + pnl_x) - fees + pos.accumulated_funding
        self.closed_positions.append(pos)
        logger.info(f"🏁 [POSITION CLOSED] {pair_name} | Net PnL: ${pos.realized_pnl:+.2f} USD | Reason: {close_reason}")
        return pos

    def get_symbol_net_quantities(self) -> Dict[str, float]:
        """Calculates expected net exposure per individual symbol across all open positions."""
        net_qty: Dict[str, float] = {}
        for pos in self.open_positions.values():
            # Leg Y
            sgn_y = 1.0 if pos.leg_y.side == 'BUY' else -1.0
            net_qty[pos.leg_y.symbol] = net_qty.get(pos.leg_y.symbol, 0.0) + (sgn_y * pos.leg_y.quantity)
            
            # Leg X
            sgn_x = 1.0 if pos.leg_x.side == 'BUY' else -1.0
            net_qty[pos.leg_x.symbol] = net_qty.get(pos.leg_x.symbol, 0.0) + (sgn_x * pos.leg_x.quantity)
        return net_qty

    def get_total_notional_exposure(self) -> float:
        """Returns aggregate gross notional exposure across all positions."""
        total = 0.0
        for pos in self.open_positions.values():
            total += (pos.leg_y.quantity * pos.leg_y.current_price)
            total += (pos.leg_x.quantity * pos.leg_x.current_price)
        return total
