import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
import json

from .black_scholes import BlackScholesCalculator, OptionParams

class PositionType(Enum):
    """Position type for options"""
    LONG = "long"
    SHORT = "short"

class OptionType(Enum):
    """Option type"""
    CALL = "call"
    PUT = "put"

@dataclass
class OptionLeg:
    """Individual option leg in a strategy"""
    option_type: OptionType
    position_type: PositionType  # long or short
    strike: float
    expiration: date
    quantity: int = 1
    premium: Optional[float] = None  # Premium paid/received
    
    def __post_init__(self):
        if isinstance(self.option_type, str):
            self.option_type = OptionType(self.option_type.lower())
        if isinstance(self.position_type, str):
            self.position_type = PositionType(self.position_type.lower())

@dataclass
class StockLeg:
    """Stock position leg"""
    position_type: PositionType  # long or short
    quantity: int
    entry_price: float
    
    def __post_init__(self):
        if isinstance(self.position_type, str):
            self.position_type = PositionType(self.position_type.lower())

@dataclass
class StrategyDefinition:
    """Complete options strategy definition"""
    name: str
    strategy_type: str  # 'straddle', 'strangle', 'spread', etc.
    option_legs: List[OptionLeg] = field(default_factory=list)
    stock_legs: List[StockLeg] = field(default_factory=list)
    description: str = ""
    created_date: Optional[date] = None
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = date.today()

@dataclass
class StrategyPnL:
    """P&L calculation result for a strategy"""
    underlying_prices: np.ndarray
    pnl_values: np.ndarray
    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    profit_probability: Optional[float] = None
    
    @property
    def profit_range(self) -> Tuple[float, float]:
        """Range where strategy is profitable"""
        profitable_prices = self.underlying_prices[self.pnl_values > 0]
        if len(profitable_prices) == 0:
            return (float('inf'), float('inf'))
        return (profitable_prices.min(), profitable_prices.max())

class OptionsStrategyBuilder:
    """Builder for creating common options strategies"""
    
    @staticmethod
    def long_call(strike: float, expiration: date, premium: Optional[float] = None) -> StrategyDefinition:
        """Create a long call strategy"""
        leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=strike,
            expiration=expiration,
            premium=premium
        )
        return StrategyDefinition(
            name=f"Long Call ${strike}",
            strategy_type="long_call",
            option_legs=[leg],
            description=f"Long call with ${strike} strike, expires {expiration}"
        )
    
    @staticmethod
    def long_put(strike: float, expiration: date, premium: Optional[float] = None) -> StrategyDefinition:
        """Create a long put strategy"""
        leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=PositionType.LONG,
            strike=strike,
            expiration=expiration,
            premium=premium
        )
        return StrategyDefinition(
            name=f"Long Put ${strike}",
            strategy_type="long_put",
            option_legs=[leg],
            description=f"Long put with ${strike} strike, expires {expiration}"
        )
    
    @staticmethod
    def covered_call(stock_price: float, call_strike: float, expiration: date,
                    stock_quantity: int = 100, call_premium: Optional[float] = None) -> StrategyDefinition:
        """Create a covered call strategy"""
        stock_leg = StockLeg(
            position_type=PositionType.LONG,
            quantity=stock_quantity,
            entry_price=stock_price
        )
        call_leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.SHORT,
            strike=call_strike,
            expiration=expiration,
            quantity=stock_quantity // 100,  # 1 contract per 100 shares
            premium=call_premium
        )
        return StrategyDefinition(
            name=f"Covered Call ${call_strike}",
            strategy_type="covered_call",
            option_legs=[call_leg],
            stock_legs=[stock_leg],
            description=f"Long {stock_quantity} shares, short call ${call_strike}"
        )
    
    @staticmethod
    def straddle(strike: float, expiration: date, call_premium: Optional[float] = None,
                put_premium: Optional[float] = None, position_type: PositionType = PositionType.LONG) -> StrategyDefinition:
        """Create a straddle strategy (long or short)"""
        call_leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=position_type,
            strike=strike,
            expiration=expiration,
            premium=call_premium
        )
        put_leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=position_type,
            strike=strike,
            expiration=expiration,
            premium=put_premium
        )
        
        name = f"{'Long' if position_type == PositionType.LONG else 'Short'} Straddle ${strike}"
        return StrategyDefinition(
            name=name,
            strategy_type="straddle",
            option_legs=[call_leg, put_leg],
            description=f"{position_type.value.title()} straddle at ${strike} strike"
        )
    
    @staticmethod
    def strangle(call_strike: float, put_strike: float, expiration: date,
                call_premium: Optional[float] = None, put_premium: Optional[float] = None,
                position_type: PositionType = PositionType.LONG) -> StrategyDefinition:
        """Create a strangle strategy (long or short)"""
        call_leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=position_type,
            strike=call_strike,
            expiration=expiration,
            premium=call_premium
        )
        put_leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=position_type,
            strike=put_strike,
            expiration=expiration,
            premium=put_premium
        )
        
        name = f"{'Long' if position_type == PositionType.LONG else 'Short'} Strangle ${put_strike}/${call_strike}"
        return StrategyDefinition(
            name=name,
            strategy_type="strangle",
            option_legs=[call_leg, put_leg],
            description=f"{position_type.value.title()} strangle: ${put_strike} put / ${call_strike} call"
        )
    
    @staticmethod
    def bull_call_spread(long_strike: float, short_strike: float, expiration: date,
                        long_premium: Optional[float] = None, short_premium: Optional[float] = None) -> StrategyDefinition:
        """Create a bull call spread"""
        long_leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.LONG,
            strike=long_strike,
            expiration=expiration,
            premium=long_premium
        )
        short_leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.SHORT,
            strike=short_strike,
            expiration=expiration,
            premium=short_premium
        )
        
        return StrategyDefinition(
            name=f"Bull Call Spread ${long_strike}/${short_strike}",
            strategy_type="bull_call_spread",
            option_legs=[long_leg, short_leg],
            description=f"Long ${long_strike} call, short ${short_strike} call"
        )
    
    @staticmethod
    def bear_put_spread(long_strike: float, short_strike: float, expiration: date,
                       long_premium: Optional[float] = None, short_premium: Optional[float] = None) -> StrategyDefinition:
        """Create a bear put spread"""
        long_leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=PositionType.LONG,
            strike=long_strike,
            expiration=expiration,
            premium=long_premium
        )
        short_leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=PositionType.SHORT,
            strike=short_strike,
            expiration=expiration,
            premium=short_premium
        )
        
        return StrategyDefinition(
            name=f"Bear Put Spread ${long_strike}/${short_strike}",
            strategy_type="bear_put_spread",
            option_legs=[long_leg, short_leg],
            description=f"Long ${long_strike} put, short ${short_strike} put"
        )
    
    @staticmethod
    def iron_condor(put_long_strike: float, put_short_strike: float,
                   call_short_strike: float, call_long_strike: float, expiration: date) -> StrategyDefinition:
        """Create an iron condor strategy"""
        put_long = OptionLeg(OptionType.PUT, PositionType.LONG, put_long_strike, expiration)
        put_short = OptionLeg(OptionType.PUT, PositionType.SHORT, put_short_strike, expiration)
        call_short = OptionLeg(OptionType.CALL, PositionType.SHORT, call_short_strike, expiration)
        call_long = OptionLeg(OptionType.CALL, PositionType.LONG, call_long_strike, expiration)
        
        return StrategyDefinition(
            name=f"Iron Condor ${put_long_strike}/${put_short_strike}/${call_short_strike}/${call_long_strike}",
            strategy_type="iron_condor",
            option_legs=[put_long, put_short, call_short, call_long],
            description=f"Iron condor with strikes {put_long_strike}/{put_short_strike}/{call_short_strike}/{call_long_strike}"
        )
    
    @staticmethod
    def butterfly_spread(center_strike: float, wing_width: float, expiration: date,
                        option_type: OptionType = OptionType.CALL) -> StrategyDefinition:
        """Create a butterfly spread"""
        lower_strike = center_strike - wing_width
        upper_strike = center_strike + wing_width
        
        lower_leg = OptionLeg(option_type, PositionType.LONG, lower_strike, expiration)
        center_leg = OptionLeg(option_type, PositionType.SHORT, center_strike, expiration, quantity=2)
        upper_leg = OptionLeg(option_type, PositionType.LONG, upper_strike, expiration)
        
        option_name = "Call" if option_type == OptionType.CALL else "Put"
        return StrategyDefinition(
            name=f"{option_name} Butterfly ${lower_strike}/${center_strike}/${upper_strike}",
            strategy_type="butterfly_spread",
            option_legs=[lower_leg, center_leg, upper_leg],
            description=f"{option_name} butterfly centered at ${center_strike} with ${wing_width} wings"
        )

class StrategyPnLCalculator:
    """Calculate P&L for options strategies"""
    
    @staticmethod
    def calculate_option_pnl(leg: OptionLeg, underlying_prices: np.ndarray,
                           current_price: float, time_to_expiry: float, 
                           volatility: float, risk_free_rate: float = 0.05) -> np.ndarray:
        """Calculate P&L for a single option leg"""
        pnl = np.zeros_like(underlying_prices)
        
        for i, S in enumerate(underlying_prices):
            if time_to_expiry <= 0:
                # At expiration - intrinsic value only
                if leg.option_type == OptionType.CALL:
                    option_value = max(S - leg.strike, 0)
                else:
                    option_value = max(leg.strike - S, 0)
            else:
                # Before expiration - use Black-Scholes
                option_value = BlackScholesCalculator.option_price(
                    S, leg.strike, time_to_expiry, risk_free_rate, 
                    volatility, leg.option_type.value
                )
            
            # Calculate P&L based on position type
            if leg.position_type == PositionType.LONG:
                leg_pnl = (option_value - (leg.premium or 0)) * leg.quantity * 100
            else:  # SHORT
                leg_pnl = ((leg.premium or 0) - option_value) * leg.quantity * 100
            
            pnl[i] = leg_pnl
        
        return pnl
    
    @staticmethod
    def calculate_stock_pnl(leg: StockLeg, underlying_prices: np.ndarray) -> np.ndarray:
        """Calculate P&L for a stock leg"""
        price_diff = underlying_prices - leg.entry_price
        
        if leg.position_type == PositionType.LONG:
            return price_diff * leg.quantity
        else:  # SHORT
            return -price_diff * leg.quantity
    
    @staticmethod
    def calculate_strategy_pnl(strategy: StrategyDefinition, underlying_prices: np.ndarray,
                             current_price: float, time_to_expiry: float,
                             volatility: float, risk_free_rate: float = 0.05) -> StrategyPnL:
        """Calculate complete strategy P&L"""
        total_pnl = np.zeros_like(underlying_prices)
        
        # Calculate P&L for each option leg
        for leg in strategy.option_legs:
            leg_pnl = StrategyPnLCalculator.calculate_option_pnl(
                leg, underlying_prices, current_price, time_to_expiry,
                volatility, risk_free_rate
            )
            total_pnl += leg_pnl
        
        # Calculate P&L for each stock leg
        for leg in strategy.stock_legs:
            leg_pnl = StrategyPnLCalculator.calculate_stock_pnl(leg, underlying_prices)
            total_pnl += leg_pnl
        
        # Find breakeven points
        breakeven_points = StrategyPnLCalculator._find_breakeven_points(underlying_prices, total_pnl)
        
        return StrategyPnL(
            underlying_prices=underlying_prices,
            pnl_values=total_pnl,
            max_profit=np.max(total_pnl),
            max_loss=np.min(total_pnl),
            breakeven_points=breakeven_points
        )
    
    @staticmethod
    def _find_breakeven_points(prices: np.ndarray, pnl: np.ndarray, tolerance: float = 0.01) -> List[float]:
        """Find breakeven points where P&L crosses zero"""
        breakevens = []
        
        for i in range(len(pnl) - 1):
            # Check if P&L crosses zero between consecutive points
            if (pnl[i] <= tolerance and pnl[i + 1] >= -tolerance) or \
               (pnl[i] >= -tolerance and pnl[i + 1] <= tolerance):
                # Linear interpolation to find exact crossing point
                if abs(pnl[i + 1] - pnl[i]) > 1e-10:  # Avoid division by zero
                    ratio = -pnl[i] / (pnl[i + 1] - pnl[i])
                    breakeven_price = prices[i] + ratio * (prices[i + 1] - prices[i])
                    breakevens.append(breakeven_price)
        
        return sorted(list(set(np.round(breakevens, 2))))
    
    @staticmethod
    def calculate_greeks(strategy: StrategyDefinition, current_price: float,
                        time_to_expiry: float, volatility: float,
                        risk_free_rate: float = 0.05) -> Dict[str, float]:
        """Calculate net Greeks for the entire strategy"""
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0
        
        for leg in strategy.option_legs:
            multiplier = leg.quantity * (1 if leg.position_type == PositionType.LONG else -1)
            
            delta = BlackScholesCalculator.delta(
                current_price, leg.strike, time_to_expiry, risk_free_rate,
                volatility, leg.option_type.value
            ) * multiplier * 100
            
            gamma = BlackScholesCalculator.gamma(
                current_price, leg.strike, time_to_expiry, risk_free_rate, volatility
            ) * multiplier * 100
            
            theta = BlackScholesCalculator.theta(
                current_price, leg.strike, time_to_expiry, risk_free_rate,
                volatility, leg.option_type.value
            ) * multiplier * 100
            
            vega = BlackScholesCalculator.vega(
                current_price, leg.strike, time_to_expiry, risk_free_rate, volatility
            ) * multiplier * 100
            
            rho = BlackScholesCalculator.rho(
                current_price, leg.strike, time_to_expiry, risk_free_rate,
                volatility, leg.option_type.value
            ) * multiplier * 100
            
            total_delta += delta
            total_gamma += gamma
            total_theta += theta
            total_vega += vega
            total_rho += rho
        
        # Add stock delta (1.0 per share)
        for leg in strategy.stock_legs:
            stock_delta = leg.quantity * (1 if leg.position_type == PositionType.LONG else -1)
            total_delta += stock_delta
        
        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega,
            'rho': total_rho
        }

# Convenience functions
def create_long_straddle(strike: float, expiration: date) -> StrategyDefinition:
    """Quick creation of long straddle"""
    return OptionsStrategyBuilder.straddle(strike, expiration, position_type=PositionType.LONG)

def create_short_straddle(strike: float, expiration: date) -> StrategyDefinition:
    """Quick creation of short straddle"""
    return OptionsStrategyBuilder.straddle(strike, expiration, position_type=PositionType.SHORT)

def create_long_strangle(put_strike: float, call_strike: float, expiration: date) -> StrategyDefinition:
    """Quick creation of long strangle"""
    return OptionsStrategyBuilder.strangle(call_strike, put_strike, expiration, position_type=PositionType.LONG)