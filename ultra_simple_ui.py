#!/usr/bin/env python3
"""
Ultra Simple Streamlit Option Chain UI
Minimal interface focusing only on option chain display and Greeks
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import timedelta, date

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.analytics.black_scholes import BlackScholesCalculator
from src.data_sources.storage import storage
from src.analytics.volatility import get_volatility_metrics

# Minimal page config
st.set_page_config(page_title="Option Chain", layout="wide")

def load_data(symbol):
    """Load price data and calculate current metrics"""
    try:
        price_data = storage.load_price_history(symbol)
        if price_data is None or len(price_data) == 0:
            return None, None, None
        
        current_price = float(price_data['close'].iloc[-1])
        vol_metrics = get_volatility_metrics(price_data)
        volatility = vol_metrics.get('hv_30d', 0.25)
        
        return current_price, volatility, len(price_data)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None

def create_option_chain(current_price, volatility, days_to_expiry, risk_free_rate):
    """Create option chain data"""
    
    # Generate strikes around current price
    strikes = []
    for mult in np.arange(0.85, 1.16, 0.025):  # 85% to 115% in 2.5% increments
        strikes.append(round(current_price * mult))
    
    T = days_to_expiry / 365.0
    
    # Calculate option data
    chain_data = []
    
    for strike in strikes:
        # Calculate option prices and Greeks
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
            status = "ITM"
        else:
            status = "OTM"
        
        chain_data.append({
            'Strike': strike,
            'Call Price': f"${call_price:.2f}",
            'Call Delta': f"{call_delta:.3f}",
            'Call Theta': f"{call_theta:.2f}",
            'Gamma': f"{gamma:.4f}",
            'Vega': f"{vega:.2f}",
            'Put Price': f"${put_price:.2f}",
            'Put Delta': f"{put_delta:.3f}",
            'Put Theta': f"{put_theta:.2f}",
            'Moneyness': status
        })
    
    return pd.DataFrame(chain_data)

def main():
    # Title
    st.title("📊 Simple Option Chain")
    
    # Simple controls in one row
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    
    with col1:
        symbol = st.selectbox("Symbol", ["AAPL", "SPY", "TSLA"], index=0)
    
    with col2:
        days_to_expiry = st.number_input("Days", min_value=1, max_value=365, value=30, step=1)
    
    with col3:
        risk_free_rate = st.number_input("Rate", min_value=0.0, max_value=0.2, value=0.05, step=0.001, format="%.3f")
    
    with col4:
        manual_price = st.number_input("Price", min_value=0.0, value=0.0, step=0.01)
    
    with col5:
        manual_vol = st.number_input("Vol", min_value=0.0, max_value=3.0, value=0.0, step=0.01)
    
    st.markdown("---")
    
    # Load data or use manual inputs
    if manual_price > 0 and manual_vol > 0:
        current_price = manual_price
        volatility = manual_vol
        data_status = "Manual Input"
    else:
        current_price, volatility, record_count = load_data(symbol)
        if current_price is None:
            st.error(f"No data found for {symbol}. Use manual inputs or run: python main.py download")
            return
        data_status = f"Live Data ({record_count} records)"
    
    # Display current info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Price", f"${current_price:.2f}")
    with col2:
        st.metric("Volatility", f"{volatility:.1%}")
    with col3:
        st.metric("Expiration", f"{days_to_expiry} days")
    with col4:
        st.metric("Data Source", data_status)
    
    st.markdown("---")
    
    # Generate and display option chain
    try:
        chain_df = create_option_chain(current_price, volatility, days_to_expiry, risk_free_rate)
        
        # Style the dataframe
        def highlight_atm(row):
            if row['Moneyness'] == 'ATM':
                return ['background-color: lightblue'] * len(row)
            elif row['Moneyness'] == 'ITM':
                return ['background-color: lightgreen'] * len(row)
            else:
                return [''] * len(row)
        
        styled_df = chain_df.style.apply(highlight_atm, axis=1)
        
        # Display the chain
        st.subheader("Option Chain")
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Quick summary
        st.markdown("---")
        st.subheader("Summary")
        
        # Find ATM option for summary
        atm_strike = min(chain_df['Strike'], key=lambda x: abs(x - current_price))
        atm_row = chain_df[chain_df['Strike'] == atm_strike].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("ATM Strike", f"${atm_strike}")
        with col2:
            st.metric("ATM Call Price", atm_row['Call Price'])
        with col3:
            st.metric("ATM Put Price", atm_row['Put Price'])
        
        # Export option
        if st.button("📥 Export to CSV"):
            csv = chain_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"{symbol}_option_chain_{date.today()}.csv",
                mime="text/csv"
            )
        
    except Exception as e:
        st.error(f"Error generating option chain: {e}")
        st.info("Try adjusting the parameters or check data availability.")

if __name__ == "__main__":
    main()