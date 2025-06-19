#!/usr/bin/env python3
"""
Simple Option Chain Display
A clean, text-based option chain viewer with Greeks calculations
"""

import sys
sys.path.append('src')

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from src.data_sources.storage import storage
from src.analytics.black_scholes import BlackScholesCalculator
from src.analytics.volatility import get_volatility_metrics

def display_option_chain(symbol='AAPL', days_to_expiry=30, risk_free_rate=0.05):
    """Display a clean option chain with Greeks"""
    
    print(f"\n📊 {symbol} Option Chain")
    print("=" * 80)
    
    # Load price data
    price_data = storage.load_price_history(symbol)
    if price_data is None:
        print(f"❌ No data found for {symbol}. Run 'python main.py download' first.")
        return
    
    current_price = price_data['close'].iloc[-1]
    print(f"Current Stock Price: ${current_price:.2f}")
    
    # Get volatility
    vol_metrics = get_volatility_metrics(price_data)
    volatility = vol_metrics.get('hv_30d', 0.25)
    print(f"30-day Historical Volatility: {volatility:.1%}")
    
    expiry_date = date.today() + timedelta(days=days_to_expiry)
    print(f"Expiration Date: {expiry_date} ({days_to_expiry} days)")
    print(f"Risk-free Rate: {risk_free_rate:.1%}")
    print()
    
    # Generate strike prices around current price
    strike_range = np.arange(
        current_price * 0.85,  # 15% OTM puts
        current_price * 1.15,  # 15% OTM calls
        current_price * 0.025  # 2.5% increments
    )
    
    # Round strikes to nearest dollar
    strikes = [round(s) for s in strike_range]
    
    T = days_to_expiry / 365.0
    
    # Calculate option data
    options_data = []
    
    for strike in strikes:
        # Calculate call and put prices and Greeks
        call_price = BlackScholesCalculator.option_price(current_price, strike, T, risk_free_rate, volatility, 'call')
        put_price = BlackScholesCalculator.option_price(current_price, strike, T, risk_free_rate, volatility, 'put')
        
        call_delta = BlackScholesCalculator.delta(current_price, strike, T, risk_free_rate, volatility, 'call')
        put_delta = BlackScholesCalculator.delta(current_price, strike, T, risk_free_rate, volatility, 'put')
        
        gamma = BlackScholesCalculator.gamma(current_price, strike, T, risk_free_rate, volatility)
        
        call_theta = BlackScholesCalculator.theta(current_price, strike, T, risk_free_rate, volatility, 'call')
        put_theta = BlackScholesCalculator.theta(current_price, strike, T, risk_free_rate, volatility, 'put')
        
        vega = BlackScholesCalculator.vega(current_price, strike, T, risk_free_rate, volatility)
        
        # Determine moneyness
        moneyness = current_price / strike
        if 0.98 <= moneyness <= 1.02:
            status = "ATM"
        elif moneyness > 1.02:
            status = "ITM" if strike < current_price else "OTM"
        else:
            status = "OTM" if strike < current_price else "ITM"
        
        options_data.append({
            'strike': strike,
            'status': status,
            'call_price': call_price,
            'call_delta': call_delta,
            'call_theta': call_theta,
            'put_price': put_price,
            'put_delta': put_delta,
            'put_theta': put_theta,
            'gamma': gamma,
            'vega': vega
        })
    
    # Display header
    print("CALLS" + " " * 35 + "STRIKE" + " " * 6 + "PUTS")
    print("-" * 80)
    print(f"{'Price':>6} {'Delta':>6} {'Theta':>6} | {'Strike':>6} {'M':>3} | {'Price':>6} {'Delta':>6} {'Theta':>6}")
    print("-" * 80)
    
    # Display option chain
    for opt in options_data:
        strike = opt['strike']
        status = opt['status']
        
        # Color coding for moneyness (using simple text indicators)
        if status == "ATM":
            marker = "🎯"
        elif (status == "ITM" and strike < current_price) or (status == "ITM" and strike > current_price):
            marker = "💰"
        else:
            marker = " - "
        
        print(f"{opt['call_price']:6.2f} {opt['call_delta']:6.3f} {opt['call_theta']:6.2f} | "
              f"{strike:6.0f} {marker} | "
              f"{opt['put_price']:6.2f} {opt['put_delta']:6.3f} {opt['put_theta']:6.2f}")
    
    print("-" * 80)
    print("Legend: 🎯 = At-the-Money, 💰 = In-the-Money, - = Out-of-the-Money")
    print()
    
    # Summary statistics
    print("📈 GREEKS SUMMARY")
    print("-" * 40)
    
    # Find ATM strike for summary
    atm_strike = min(strikes, key=lambda x: abs(x - current_price))
    atm_data = next(opt for opt in options_data if opt['strike'] == atm_strike)
    
    print(f"ATM Strike: ${atm_strike}")
    print(f"Gamma:      {atm_data['gamma']:.4f}")
    print(f"Vega:       ${atm_data['vega']:.2f} per 1% vol change")
    print()
    
    # Volatility impact analysis
    print("💫 VOLATILITY IMPACT (ATM Call)")
    print("-" * 40)
    vol_scenarios = [volatility * 0.8, volatility, volatility * 1.2]
    
    for vol in vol_scenarios:
        scenario_price = BlackScholesCalculator.option_price(
            current_price, atm_strike, T, risk_free_rate, vol, 'call'
        )
        change = scenario_price - atm_data['call_price']
        print(f"Vol {vol:5.1%}: ${scenario_price:5.2f} ({change:+5.2f})")
    
    print()

def interactive_mode():
    """Interactive mode for exploring different scenarios"""
    print("\n🎮 Interactive Option Chain Viewer")
    print("Type 'help' for commands, 'quit' to exit")
    
    # Default values
    symbol = 'AAPL'
    days = 30
    rate = 0.05
    
    while True:
        try:
            cmd = input(f"\n[{symbol}, {days}d, {rate:.1%}] > ").strip().lower()
            
            if cmd == 'quit' or cmd == 'q':
                break
            elif cmd == 'help' or cmd == 'h':
                print("\nCommands:")
                print("  show                - Display current option chain")
                print("  symbol <SYM>       - Change symbol (e.g., 'symbol SPY')")
                print("  days <N>           - Change days to expiry (e.g., 'days 60')")
                print("  rate <R>           - Change risk-free rate (e.g., 'rate 0.04')")
                print("  quick              - Quick 7/14/30/60 day comparison")
                print("  help               - Show this help")
                print("  quit               - Exit")
            elif cmd == 'show' or cmd == '':
                display_option_chain(symbol, days, rate)
            elif cmd.startswith('symbol '):
                new_symbol = cmd.split()[1].upper()
                symbol = new_symbol
                print(f"Symbol changed to {symbol}")
            elif cmd.startswith('days '):
                try:
                    new_days = int(cmd.split()[1])
                    days = new_days
                    print(f"Days to expiry changed to {days}")
                except:
                    print("Invalid days format. Use: days 30")
            elif cmd.startswith('rate '):
                try:
                    new_rate = float(cmd.split()[1])
                    rate = new_rate
                    print(f"Risk-free rate changed to {rate:.1%}")
                except:
                    print("Invalid rate format. Use: rate 0.05")
            elif cmd == 'quick':
                print(f"\n📊 Quick Comparison for {symbol}")
                for d in [7, 14, 30, 60]:
                    print(f"\n--- {d} Days ---")
                    display_option_chain(symbol, d, rate)
            else:
                print("Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ['interactive', 'i']:
            interactive_mode()
        elif sys.argv[1].lower() in ['help', 'h']:
            print("\nSimple Option Chain Display")
            print("Usage:")
            print("  python simple_option_chain.py              - Show AAPL 30-day chain")
            print("  python simple_option_chain.py interactive  - Interactive mode")
            print("  python simple_option_chain.py <SYMBOL>     - Show specific symbol")
            print()
        else:
            # Treat as symbol
            symbol = sys.argv[1].upper()
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            display_option_chain(symbol, days)
    else:
        # Default: show AAPL 30-day chain
        display_option_chain()

if __name__ == "__main__":
    main()