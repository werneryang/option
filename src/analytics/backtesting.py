import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum

from .strategies import StrategyDefinition, StrategyPnLCalculator, StrategyPnL, OptionLeg, StockLeg
from .volatility import HistoricalVolatilityCalculator
from .black_scholes import BlackScholesCalculator

class ExitCondition(Enum):
    """Exit conditions for backtesting"""
    EXPIRATION = "expiration"
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    DAYS_TO_EXPIRY = "days_to_expiry"
    DELTA_THRESHOLD = "delta_threshold"

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    start_date: date
    end_date: date
    entry_frequency: int = 30  # Days between entries
    profit_target: Optional[float] = None  # % of max profit
    stop_loss: Optional[float] = None  # % of max loss
    min_days_to_expiry: int = 5  # Minimum DTE before forced exit
    risk_free_rate: float = 0.05
    volatility_lookback: int = 30  # Days for volatility calculation
    commission_per_contract: float = 1.0

@dataclass
class TradeResult:
    """Result of a single trade"""
    entry_date: date
    exit_date: date
    entry_price: float  # Underlying price at entry
    exit_price: float   # Underlying price at exit
    strategy_cost: float  # Net premium paid/received
    pnl: float  # Total P&L including commissions
    pnl_percent: float  # P&L as percentage of capital at risk
    days_held: int
    exit_reason: ExitCondition
    max_profit_during_trade: float
    max_loss_during_trade: float
    volatility_at_entry: float
    delta_at_entry: float
    theta_at_entry: float

@dataclass
class BacktestResult:
    """Complete backtesting result"""
    config: BacktestConfig
    trades: List[TradeResult]
    total_return: float
    win_rate: float
    avg_win: float
    avg_loss: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    total_commissions: float
    
    @property
    def total_trades(self) -> int:
        return len(self.trades)
    
    @property
    def winning_trades(self) -> int:
        return sum(1 for trade in self.trades if trade.pnl > 0)
    
    @property
    def losing_trades(self) -> int:
        return sum(1 for trade in self.trades if trade.pnl < 0)

class StrategyBacktester:
    """Backtest options strategies using historical data"""
    
    def __init__(self, price_data: pd.DataFrame):
        """
        Initialize backtester with historical price data
        
        Args:
            price_data: DataFrame with columns: date, open, high, low, close, volume
        """
        self.price_data = price_data.sort_values('date').reset_index(drop=True)
        self.price_data['date'] = pd.to_datetime(self.price_data['date']).dt.date
    
    def backtest_strategy(self, strategy_template: StrategyDefinition, 
                         config: BacktestConfig) -> BacktestResult:
        """
        Backtest a strategy over historical data
        
        Args:
            strategy_template: Template strategy (strikes will be adjusted for each entry)
            config: Backtesting configuration
            
        Returns:
            BacktestResult with detailed performance metrics
        """
        trades = []
        current_date = config.start_date
        
        while current_date <= config.end_date:
            # Find entry date in data
            entry_data = self._find_trading_date(current_date)
            if entry_data is None:
                current_date += timedelta(days=1)
                continue
            
            # Create strategy for this entry
            strategy = self._create_strategy_for_entry(strategy_template, entry_data)
            if strategy is None:
                current_date += timedelta(days=config.entry_frequency)
                continue
            
            # Execute trade
            trade_result = self._execute_trade(strategy, entry_data, config)
            if trade_result:
                trades.append(trade_result)
            
            # Move to next entry date
            current_date += timedelta(days=config.entry_frequency)
        
        # Calculate backtest metrics
        return self._calculate_backtest_metrics(trades, config)
    
    def _find_trading_date(self, target_date: date) -> Optional[pd.Series]:
        """Find the closest trading date to target date"""
        available_dates = self.price_data['date']
        
        # Find exact match or next available date
        exact_match = self.price_data[available_dates == target_date]
        if not exact_match.empty:
            return exact_match.iloc[0]
        
        # Find next available date
        future_dates = self.price_data[available_dates > target_date]
        if not future_dates.empty:
            return future_dates.iloc[0]
        
        return None
    
    def _create_strategy_for_entry(self, template: StrategyDefinition, 
                                  entry_data: pd.Series) -> Optional[StrategyDefinition]:
        """Create strategy with strikes relative to current price"""
        current_price = entry_data['close']
        
        # Create new strategy based on template
        strategy = StrategyDefinition(
            name=template.name,
            strategy_type=template.strategy_type,
            description=template.description
        )
        
        # Adjust option strikes relative to current price
        for leg in template.option_legs:
            # For template strategies, strikes are often relative (e.g., ATM = 1.0)
            if leg.strike <= 10:  # Assume relative strike (multiplier)
                adjusted_strike = current_price * leg.strike
            else:  # Absolute strike
                adjusted_strike = leg.strike
            
            # Round strike to nearest $0.50 for realistic options
            adjusted_strike = round(adjusted_strike * 2) / 2
            
            new_leg = OptionLeg(
                option_type=leg.option_type,
                position_type=leg.position_type,
                strike=adjusted_strike,
                expiration=leg.expiration,
                quantity=leg.quantity
            )
            strategy.option_legs.append(new_leg)
        
        # Copy stock legs as-is (adjust price to current)
        for leg in template.stock_legs:
            new_leg = StockLeg(
                position_type=leg.position_type,
                quantity=leg.quantity,
                entry_price=current_price
            )
            strategy.stock_legs.append(new_leg)
        
        return strategy
    
    def _execute_trade(self, strategy: StrategyDefinition, entry_data: pd.Series,
                      config: BacktestConfig) -> Optional[TradeResult]:
        """Execute a single trade from entry to exit"""
        entry_date = entry_data['date']
        entry_price = entry_data['close']
        
        # Calculate volatility at entry
        entry_index = self.price_data[self.price_data['date'] == entry_date].index[0]
        historical_data = self.price_data.iloc[:entry_index + 1]
        
        if len(historical_data) < config.volatility_lookback:
            return None
        
        vol_result = HistoricalVolatilityCalculator.simple_volatility(
            historical_data, config.volatility_lookback
        )
        if not vol_result:
            return None
        
        volatility = vol_result.volatility
        
        # Calculate strategy cost and Greeks at entry
        time_to_expiry = self._calculate_time_to_expiry(strategy, entry_date)
        if time_to_expiry <= 0:
            return None
        
        strategy_cost = self._calculate_strategy_cost(
            strategy, entry_price, time_to_expiry, volatility, config.risk_free_rate
        )
        
        greeks = StrategyPnLCalculator.calculate_greeks(
            strategy, entry_price, time_to_expiry, volatility, config.risk_free_rate
        )
        
        # Track trade progression
        exit_date = None
        exit_price = None
        exit_reason = ExitCondition.EXPIRATION
        max_profit = 0
        max_loss = 0
        
        # Simulate trade day by day
        trade_dates = self.price_data[
            (self.price_data['date'] > entry_date) &
            (self.price_data['date'] <= strategy.option_legs[0].expiration)
        ]
        
        for _, day_data in trade_dates.iterrows():
            current_date = day_data['date']
            current_price = day_data['close']
            
            # Calculate current time to expiry
            current_tte = self._calculate_time_to_expiry(strategy, current_date)
            
            # Calculate current P&L
            pnl_calc = StrategyPnLCalculator.calculate_strategy_pnl(
                strategy, np.array([current_price]), entry_price, 
                current_tte, volatility, config.risk_free_rate
            )
            current_pnl = pnl_calc.pnl_values[0] - strategy_cost
            
            # Update max profit/loss
            max_profit = max(max_profit, current_pnl)
            max_loss = min(max_loss, current_pnl)
            
            # Check exit conditions
            exit_triggered = False
            
            # Profit target
            if config.profit_target and current_pnl > 0:
                target_profit = abs(strategy_cost) * config.profit_target
                if current_pnl >= target_profit:
                    exit_reason = ExitCondition.PROFIT_TARGET
                    exit_triggered = True
            
            # Stop loss
            if config.stop_loss and current_pnl < 0:
                stop_loss_amount = abs(strategy_cost) * config.stop_loss
                if current_pnl <= -stop_loss_amount:
                    exit_reason = ExitCondition.STOP_LOSS
                    exit_triggered = True
            
            # Days to expiry
            if current_tte <= config.min_days_to_expiry / 365.0:
                exit_reason = ExitCondition.DAYS_TO_EXPIRY
                exit_triggered = True
            
            if exit_triggered:
                exit_date = current_date
                exit_price = current_price
                break
        
        # If no exit triggered, exit at expiration
        if exit_date is None:
            expiration_data = self.price_data[
                self.price_data['date'] <= strategy.option_legs[0].expiration
            ]
            if not expiration_data.empty:
                last_data = expiration_data.iloc[-1]
                exit_date = last_data['date']
                exit_price = last_data['close']
                exit_reason = ExitCondition.EXPIRATION
        
        if exit_date is None:
            return None
        
        # Calculate final P&L
        exit_tte = self._calculate_time_to_expiry(strategy, exit_date)
        final_pnl_calc = StrategyPnLCalculator.calculate_strategy_pnl(
            strategy, np.array([exit_price]), entry_price, 
            exit_tte, volatility, config.risk_free_rate
        )
        final_pnl = final_pnl_calc.pnl_values[0] - strategy_cost
        
        # Add commissions
        total_contracts = sum(leg.quantity for leg in strategy.option_legs)
        commission = total_contracts * config.commission_per_contract * 2  # Entry + exit
        final_pnl -= commission
        
        # Calculate percentage return
        capital_at_risk = abs(strategy_cost) if strategy_cost < 0 else max(abs(strategy_cost), 1000)
        pnl_percent = (final_pnl / capital_at_risk) * 100
        
        days_held = (exit_date - entry_date).days
        
        return TradeResult(
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            strategy_cost=strategy_cost,
            pnl=final_pnl,
            pnl_percent=pnl_percent,
            days_held=days_held,
            exit_reason=exit_reason,
            max_profit_during_trade=max_profit,
            max_loss_during_trade=max_loss,
            volatility_at_entry=volatility,
            delta_at_entry=greeks['delta'],
            theta_at_entry=greeks['theta']
        )
    
    def _calculate_time_to_expiry(self, strategy: StrategyDefinition, current_date: date) -> float:
        """Calculate time to expiry in years"""
        if not strategy.option_legs:
            return 0.0
        
        expiration = strategy.option_legs[0].expiration
        return max((expiration - current_date).days / 365.0, 0.0)
    
    def _calculate_strategy_cost(self, strategy: StrategyDefinition, current_price: float,
                               time_to_expiry: float, volatility: float, risk_free_rate: float) -> float:
        """Calculate net cost of strategy (premium paid/received)"""
        total_cost = 0.0
        
        for leg in strategy.option_legs:
            option_price = BlackScholesCalculator.option_price(
                current_price, leg.strike, time_to_expiry, risk_free_rate,
                volatility, leg.option_type.value
            )
            
            leg_cost = option_price * leg.quantity * 100
            if leg.position_type.value == 'long':
                total_cost += leg_cost  # Pay premium
            else:
                total_cost -= leg_cost  # Receive premium
        
        return total_cost
    
    def _calculate_backtest_metrics(self, trades: List[TradeResult], 
                                   config: BacktestConfig) -> BacktestResult:
        """Calculate comprehensive backtest performance metrics"""
        if not trades:
            return BacktestResult(
                config=config, trades=[], total_return=0.0, win_rate=0.0,
                avg_win=0.0, avg_loss=0.0, max_drawdown=0.0, sharpe_ratio=0.0,
                profit_factor=0.0, total_commissions=0.0
            )
        
        # Basic metrics
        total_pnl = sum(trade.pnl for trade in trades)
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0.0
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0.0
        
        # Calculate drawdown
        cumulative_pnl = np.cumsum([t.pnl for t in trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0
        
        # Sharpe ratio (annualized)
        if len(trades) > 1:
            returns = np.array([t.pnl_percent for t in trades])
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                # Annualize based on average holding period
                avg_days_held = np.mean([t.days_held for t in trades])
                trades_per_year = 365 / avg_days_held if avg_days_held > 0 else 1
                sharpe_ratio = (avg_return * np.sqrt(trades_per_year)) / std_return
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # Profit factor
        total_wins = sum(t.pnl for t in winning_trades) if winning_trades else 0.0
        total_losses = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Total commissions (already included in trade P&L)
        total_commissions = len(trades) * config.commission_per_contract * 2
        
        # Estimate total return as percentage
        # Use average capital at risk as baseline
        avg_capital = np.mean([abs(t.strategy_cost) for t in trades]) if trades else 1.0
        total_return = (total_pnl / avg_capital) * 100 if avg_capital > 0 else 0.0
        
        return BacktestResult(
            config=config,
            trades=trades,
            total_return=total_return,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            total_commissions=total_commissions
        )

# Convenience functions
def quick_backtest(strategy_template: StrategyDefinition, price_data: pd.DataFrame,
                  start_date: date, end_date: date, **kwargs) -> BacktestResult:
    """Quick backtest with default configuration"""
    config = BacktestConfig(start_date=start_date, end_date=end_date, **kwargs)
    backtester = StrategyBacktester(price_data)
    return backtester.backtest_strategy(strategy_template, config)

def analyze_trade_distribution(trades: List[TradeResult]) -> Dict[str, float]:
    """Analyze distribution of trade results"""
    if not trades:
        return {}
    
    pnls = [t.pnl for t in trades]
    
    return {
        'total_trades': len(trades),
        'mean_pnl': np.mean(pnls),
        'median_pnl': np.median(pnls),
        'std_pnl': np.std(pnls),
        'min_pnl': np.min(pnls),
        'max_pnl': np.max(pnls),
        'percentile_25': np.percentile(pnls, 25),
        'percentile_75': np.percentile(pnls, 75),
        'skewness': float(pd.Series(pnls).skew()),
        'kurtosis': float(pd.Series(pnls).kurtosis())
    }