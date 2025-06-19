#!/usr/bin/env python3

import sys
sys.path.append('src')

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from src.data_sources.storage import storage
from src.analytics.strategies import (
    OptionsStrategyBuilder, StrategyPnLCalculator, PositionType, OptionType
)
from src.analytics.backtesting import StrategyBacktester, BacktestConfig, quick_backtest
from src.analytics.volatility import HistoricalVolatilityCalculator

def test_strategy_builder():
    """Test the strategy builder with various common strategies"""
    print("🏗️  Testing Options Strategy Builder")
    print("=" * 60)
    
    # Create expiration date (30 days from now)
    expiration = date.today() + timedelta(days=30)
    current_price = 195.64  # AAPL current price
    
    print(f"Current Price: ${current_price:.2f}")
    print(f"Expiration: {expiration}")
    print()
    
    # Test various strategies
    strategies = []
    
    # 1. Long Straddle
    straddle = OptionsStrategyBuilder.straddle(current_price, expiration, position_type=PositionType.LONG)
    strategies.append(("Long Straddle", straddle))
    
    # 2. Short Strangle
    strangle = OptionsStrategyBuilder.strangle(
        call_strike=current_price * 1.05,
        put_strike=current_price * 0.95,
        expiration=expiration,
        position_type=PositionType.SHORT
    )
    strategies.append(("Short Strangle", strangle))
    
    # 3. Bull Call Spread
    bull_spread = OptionsStrategyBuilder.bull_call_spread(
        long_strike=current_price,
        short_strike=current_price * 1.05,
        expiration=expiration
    )
    strategies.append(("Bull Call Spread", bull_spread))
    
    # 4. Iron Condor
    iron_condor = OptionsStrategyBuilder.iron_condor(
        put_long_strike=current_price * 0.90,
        put_short_strike=current_price * 0.95,
        call_short_strike=current_price * 1.05,
        call_long_strike=current_price * 1.10,
        expiration=expiration
    )
    strategies.append(("Iron Condor", iron_condor))
    
    # 5. Covered Call
    covered_call = OptionsStrategyBuilder.covered_call(
        stock_price=current_price,
        call_strike=current_price * 1.05,
        expiration=expiration
    )
    strategies.append(("Covered Call", covered_call))
    
    # Display strategy details
    for name, strategy in strategies:
        print(f"📊 {name}")
        print(f"   Type: {strategy.strategy_type}")
        print(f"   Legs: {len(strategy.option_legs)} options, {len(strategy.stock_legs)} stock")
        
        for i, leg in enumerate(strategy.option_legs):
            pos_type = "Long" if leg.position_type == PositionType.LONG else "Short"
            opt_type = "Call" if leg.option_type == OptionType.CALL else "Put"
            print(f"     {i+1}. {pos_type} {opt_type} ${leg.strike:.2f} x{leg.quantity}")
        
        for i, leg in enumerate(strategy.stock_legs):
            pos_type = "Long" if leg.position_type == PositionType.LONG else "Short"
            print(f"     Stock: {pos_type} {leg.quantity} shares @ ${leg.entry_price:.2f}")
        
        print()
    
    return strategies

def test_pnl_calculations():
    """Test P&L calculations for strategies"""
    print("💰 Testing P&L Calculations")
    print("=" * 60)
    
    # Create a simple long straddle for testing
    current_price = 195.64
    expiration = date.today() + timedelta(days=30)
    time_to_expiry = 30 / 365.0
    volatility = 0.25  # 25% implied volatility
    
    straddle = OptionsStrategyBuilder.straddle(current_price, expiration, position_type=PositionType.LONG)
    
    # Create price range for P&L calculation
    price_range = np.linspace(current_price * 0.8, current_price * 1.2, 50)
    
    # Calculate P&L at expiration (T=0)
    pnl_expiration = StrategyPnLCalculator.calculate_strategy_pnl(
        straddle, price_range, current_price, 0.0, volatility
    )
    
    # Calculate P&L with time remaining (T=30 days)
    pnl_30days = StrategyPnLCalculator.calculate_strategy_pnl(
        straddle, price_range, current_price, time_to_expiry, volatility
    )
    
    print(f"Long Straddle @ ${current_price:.2f}")
    print(f"Max Profit at Expiration: ${pnl_expiration.max_profit:.2f}")
    print(f"Max Loss at Expiration: ${pnl_expiration.max_loss:.2f}")
    print(f"Breakeven Points: {[f'${bp:.2f}' for bp in pnl_expiration.breakeven_points]}")
    print()
    
    print(f"With 30 Days Remaining:")
    print(f"Max Profit: ${pnl_30days.max_profit:.2f}")
    print(f"Max Loss: ${pnl_30days.max_loss:.2f}")
    print(f"Breakeven Points: {[f'${bp:.2f}' for bp in pnl_30days.breakeven_points]}")
    print()
    
    # Test Greeks calculation
    greeks = StrategyPnLCalculator.calculate_greeks(
        straddle, current_price, time_to_expiry, volatility
    )
    
    print("Strategy Greeks:")
    print(f"  Delta: {greeks['delta']:.2f}")
    print(f"  Gamma: {greeks['gamma']:.4f}")
    print(f"  Theta: ${greeks['theta']:.2f} per day")
    print(f"  Vega:  ${greeks['vega']:.2f} per 1% vol")
    print(f"  Rho:   ${greeks['rho']:.2f} per 1% rate")
    print()
    
    return pnl_expiration, pnl_30days

def test_backtesting():
    """Test backtesting framework with AAPL data"""
    print("🔙 Testing Strategy Backtesting")
    print("=" * 60)
    
    # Load AAPL price data
    price_data = storage.load_price_history('AAPL')
    if price_data is None:
        print("❌ No AAPL data found. Skipping backtest.")
        return
    
    print(f"Loaded {len(price_data)} days of AAPL data")
    print(f"Date range: {price_data['date'].min()} to {price_data['date'].max()}")
    print()
    
    # Create a simple strategy template for backtesting
    # Using relative strikes that will be adjusted to current price
    template_expiration = date(2025, 7, 18)  # Fixed expiration for template
    
    # Long straddle template (ATM)
    straddle_template = OptionsStrategyBuilder.straddle(
        strike=1.0,  # This will be multiplied by current price (ATM)
        expiration=template_expiration,
        position_type=PositionType.LONG
    )
    
    # Set up backtest configuration
    start_date = date(2024, 7, 1)
    end_date = date(2025, 3, 1)
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        entry_frequency=30,  # Enter trade every 30 days
        profit_target=0.5,   # Exit at 50% of max profit
        stop_loss=2.0,       # Stop loss at 200% of premium paid
        min_days_to_expiry=7,
        commission_per_contract=1.0
    )
    
    print("Backtest Configuration:")
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Entry Frequency: {config.entry_frequency} days")
    print(f"  Profit Target: {config.profit_target*100:.0f}%")
    print(f"  Stop Loss: {config.stop_loss*100:.0f}%")
    print(f"  Min DTE: {config.min_days_to_expiry} days")
    print()
    
    # Run backtest
    print("Running backtest...")
    try:
        backtester = StrategyBacktester(price_data)
        result = backtester.backtest_strategy(straddle_template, config)
        
        print("✅ Backtest Results:")
        print(f"  Total Trades: {result.total_trades}")
        print(f"  Win Rate: {result.win_rate:.1%}")
        print(f"  Total Return: {result.total_return:.1f}%")
        print(f"  Average Win: ${result.avg_win:.2f}")
        print(f"  Average Loss: ${result.avg_loss:.2f}")
        print(f"  Max Drawdown: ${result.max_drawdown:.2f}")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print(f"  Total Commissions: ${result.total_commissions:.2f}")
        print()
        
        if result.trades:
            print("Sample Trades:")
            for i, trade in enumerate(result.trades[:3]):  # Show first 3 trades
                print(f"  Trade {i+1}:")
                print(f"    Entry: {trade.entry_date} @ ${trade.entry_price:.2f}")
                print(f"    Exit:  {trade.exit_date} @ ${trade.exit_price:.2f}")
                print(f"    P&L:   ${trade.pnl:.2f} ({trade.pnl_percent:.1f}%)")
                print(f"    Held:  {trade.days_held} days")
                print(f"    Exit:  {trade.exit_reason.value}")
                print()
        
        return result
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run all strategy tests"""
    print("🚀 Options Strategy & Backtesting Engine Test")
    print("=" * 70)
    print()
    
    # Test 1: Strategy Builder
    strategies = test_strategy_builder()
    
    # Test 2: P&L Calculations
    pnl_results = test_pnl_calculations()
    
    # Test 3: Backtesting
    backtest_result = test_backtesting()
    
    print("✅ All Strategy Tests Complete!")
    print()
    print("💡 Key Features Demonstrated:")
    print("   • Multi-leg strategy creation")
    print("   • P&L calculation at any time/price")
    print("   • Greeks calculation for strategies")
    print("   • Historical backtesting framework")
    print("   • Risk metrics and performance analysis")
    print("   • Common strategies: Straddle, Strangle, Spreads, Iron Condor")

if __name__ == "__main__":
    main()