#!/usr/bin/env python3

import sys
sys.path.append('src')

import pandas as pd
import numpy as np
from datetime import datetime, date
from src.data_sources.storage import storage
from src.analytics.black_scholes import BlackScholesCalculator, OptionParams, calculate_greeks
from src.analytics.volatility import HistoricalVolatilityCalculator, get_volatility_metrics
from src.analytics.implied_volatility import ImpliedVolatilityCalculator

def test_analytics_with_aapl():
    """Test analytics engine with real AAPL historical data"""
    print("🔬 Testing Options Analytics Engine with AAPL Data")
    print("=" * 60)
    
    # Load AAPL price data
    print("📊 Loading AAPL historical data...")
    price_data = storage.load_price_history('AAPL')
    
    if price_data is None:
        print("❌ No AAPL data found. Run 'python main.py download' first.")
        return
    
    current_price = price_data['close'].iloc[-1]
    print(f"Current AAPL Price: ${current_price:.2f}")
    print(f"Data Range: {price_data['date'].min()} to {price_data['date'].max()}")
    print(f"Total Records: {len(price_data)}")
    print()
    
    # Test Historical Volatility
    print("📈 Historical Volatility Analysis")
    print("-" * 40)
    
    # Calculate multiple period volatilities
    periods = [10, 20, 30, 60, 90, 252]
    for period in periods:
        hv_result = HistoricalVolatilityCalculator.simple_volatility(price_data, period)
        if hv_result:
            print(f"  {period:3d}-day HV: {hv_result.volatility:.1%}")
    
    # Get comprehensive volatility metrics
    vol_metrics = get_volatility_metrics(price_data)
    hv_percentile = vol_metrics.get('hv_percentile')
    if hv_percentile is not None:
        print(f"\n🎯 30-day HV Percentile: {hv_percentile:.1f}")
    else:
        print(f"\n🎯 30-day HV Percentile: N/A")
    print()
    
    # Test Black-Scholes Pricing
    print("⚡ Black-Scholes Option Pricing")
    print("-" * 40)
    
    # Use 30-day historical volatility for option pricing
    hv_30d = vol_metrics.get('hv_30d', 0.25)  # Default to 25% if not available
    
    # Create sample option scenarios
    strikes = [current_price * mult for mult in [0.9, 0.95, 1.0, 1.05, 1.1]]
    expirations = [30, 60, 90]  # Days to expiration
    risk_free_rate = 0.05
    
    print(f"Using 30-day HV: {hv_30d:.1%} as volatility estimate")
    print()
    
    for dte in expirations:
        print(f"📅 {dte} Days to Expiration:")
        T = dte / 365.0
        
        for strike in strikes:
            # Calculate for both calls and puts
            call_params = OptionParams(
                S=current_price, K=strike, T=T, r=risk_free_rate, 
                sigma=hv_30d, option_type='call'
            )
            put_params = OptionParams(
                S=current_price, K=strike, T=T, r=risk_free_rate,
                sigma=hv_30d, option_type='put'
            )
            
            call_result = BlackScholesCalculator.calculate_option(call_params)
            put_result = BlackScholesCalculator.calculate_option(put_params)
            
            moneyness = strike / current_price
            print(f"  Strike ${strike:6.2f} ({moneyness:5.1%}): "
                  f"Call ${call_result.price:5.2f} (Δ{call_result.delta:5.2f}) | "
                  f"Put ${put_result.price:5.2f} (Δ{put_result.delta:6.2f})")
        print()
    
    # Test Greeks in detail for ATM option
    print("🔢 Greeks Analysis (ATM, 30 DTE)")
    print("-" * 40)
    
    atm_strike = current_price
    T_30d = 30 / 365.0
    
    atm_call = OptionParams(
        S=current_price, K=atm_strike, T=T_30d, r=risk_free_rate,
        sigma=hv_30d, option_type='call'
    )
    
    call_result = BlackScholesCalculator.calculate_option(atm_call)
    
    print(f"ATM Call (${atm_strike:.2f} strike, 30 DTE):")
    print(f"  Price:  ${call_result.price:.3f}")
    print(f"  Delta:  {call_result.delta:.4f}")
    print(f"  Gamma:  {call_result.gamma:.6f}")
    print(f"  Theta:  ${call_result.theta:.3f} per day")
    print(f"  Vega:   ${call_result.vega:.3f} per 1% vol")
    print(f"  Rho:    ${call_result.rho:.3f} per 1% rate")
    print()
    
    # Test IV calculation (reverse engineering)
    print("🔍 Implied Volatility Test")
    print("-" * 40)
    
    # Use our calculated price as "market price" and see if we can recover the IV
    market_price = call_result.price
    calculated_iv = ImpliedVolatilityCalculator.calculate_iv_from_price(
        market_price, current_price, atm_strike, T_30d, risk_free_rate, 'call'
    )
    
    print(f"Input Volatility:      {hv_30d:.4f} ({hv_30d:.1%})")
    print(f"Calculated IV:         {calculated_iv:.4f} ({calculated_iv:.1%})")
    print(f"Difference:           {abs(hv_30d - calculated_iv):.6f}")
    print()
    
    # Volatility surface data
    print("📊 Sample Volatility Surface")
    print("-" * 40)
    
    surface_data = HistoricalVolatilityCalculator.volatility_surface_data(price_data)
    if not surface_data.empty:
        print("Historical Volatility by Method and Period:")
        pivot = surface_data.pivot(index='method', columns='period_days', values='annualized_vol_pct')
        print(pivot.round(1))
    else:
        print("Could not generate volatility surface (insufficient OHLC data)")
    
    print("\n✅ Analytics Engine Test Complete!")
    print("\n💡 Key Features Demonstrated:")
    print("   • Historical volatility calculation (multiple periods)")
    print("   • Black-Scholes option pricing")
    print("   • Complete Greeks calculation (Δ, Γ, Θ, ν, ρ)")
    print("   • Implied volatility calculation")
    print("   • Volatility percentile ranking")
    print("   • Multi-method volatility analysis")

if __name__ == "__main__":
    test_analytics_with_aapl()