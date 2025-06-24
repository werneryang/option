#!/usr/bin/env python3
"""
Quick Options Calculator - Minimal Interface

Ultra-simplified calculator for fast options analysis.
Single page with just the essential calculations.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.analytics.black_scholes import BlackScholesCalculator

st.set_page_config(page_title="Options Calculator", page_icon="⚡", layout="wide")

def main():
    st.title("⚡ Quick Options Calculator")
    
    # Single row of inputs
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        S = st.number_input("Stock Price", 10.0, 1000.0, 150.0, 1.0)
    with col2:
        K = st.number_input("Strike", 10.0, 1000.0, 155.0, 1.0)
    with col3:
        T = st.number_input("Days", 1, 365, 30, 1) / 365.0
    with col4:
        r = st.number_input("Rate", 0.0, 0.2, 0.05, 0.001, format="%.3f")
    with col5:
        vol = st.number_input("Vol", 0.05, 3.0, 0.25, 0.01)
    with col6:
        strategy = st.selectbox("Quick Strategy", ["Single Options", "Straddle", "Strangle"])
    
    st.markdown("---")
    
    if strategy == "Single Options":
        # Calculate options values
        call_price = BlackScholesCalculator.option_price(S, K, T, r, vol, 'call')
        put_price = BlackScholesCalculator.option_price(S, K, T, r, vol, 'put')
        
        call_delta = BlackScholesCalculator.delta(S, K, T, r, vol, 'call')
        put_delta = BlackScholesCalculator.delta(S, K, T, r, vol, 'put')
        gamma = BlackScholesCalculator.gamma(S, K, T, r, vol)
        call_theta = BlackScholesCalculator.theta(S, K, T, r, vol, 'call')
        put_theta = BlackScholesCalculator.theta(S, K, T, r, vol, 'put')
        vega = BlackScholesCalculator.vega(S, K, T, r, vol)
        
        # Display results in clean table
        results = pd.DataFrame({
            'Metric': ['Price', 'Delta', 'Gamma', 'Theta', 'Vega'],
            'Call': [f'${call_price:.2f}', f'{call_delta:.3f}', f'{gamma:.4f}', f'{call_theta:.3f}', f'{vega:.3f}'],
            'Put': [f'${put_price:.2f}', f'{put_delta:.3f}', f'{gamma:.4f}', f'{put_theta:.3f}', f'{vega:.3f}']
        })
        
        st.dataframe(results, hide_index=True, use_container_width=True)
        
        # Moneyness indicator
        moneyness = S / K
        if 0.98 <= moneyness <= 1.02:
            st.success("🎯 At-the-Money")
        elif moneyness > 1.02:
            st.info("📈 Calls ITM, Puts OTM")
        else:
            st.info("📉 Puts ITM, Calls OTM")
    
    elif strategy == "Straddle":
        call_price = BlackScholesCalculator.option_price(S, K, T, r, vol, 'call')
        put_price = BlackScholesCalculator.option_price(S, K, T, r, vol, 'put')
        total_cost = call_price + put_price
        
        breakeven_up = K + total_cost
        breakeven_down = K - total_cost
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cost", f"${total_cost:.2f}")
        with col2:
            st.metric("Upside Breakeven", f"${breakeven_up:.2f}")
        with col3:
            st.metric("Downside Breakeven", f"${breakeven_down:.2f}")
        
        # Quick P&L visualization
        prices = np.linspace(S * 0.7, S * 1.3, 50)
        pnl = np.maximum(prices - K, 0) + np.maximum(K - prices, 0) - total_cost
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=prices, y=pnl, fill='tonexty', name='P&L'))
        fig.add_hline(y=0, line_color="black")
        fig.add_vline(x=S, line_dash="dash", annotation_text="Current")
        fig.update_layout(title="Straddle P&L", height=300, margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig, use_container_width=True)
    
    elif strategy == "Strangle":
        st.info("Strangle: Set different strikes for calls and puts")
        
        col1, col2 = st.columns(2)
        with col1:
            put_strike = st.number_input("Put Strike", 10.0, 1000.0, S * 0.95, 1.0)
        with col2:
            call_strike = st.number_input("Call Strike", 10.0, 1000.0, S * 1.05, 1.0)
        
        call_price = BlackScholesCalculator.option_price(S, call_strike, T, r, vol, 'call')
        put_price = BlackScholesCalculator.option_price(S, put_strike, T, r, vol, 'put')
        total_cost = call_price + put_price
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cost", f"${total_cost:.2f}")
        with col2:
            st.metric("Call Breakeven", f"${call_strike + total_cost:.2f}")
        with col3:
            st.metric("Put Breakeven", f"${put_strike - total_cost:.2f}")
    
    # Quick volatility reference
    st.markdown("---")
    st.markdown("**Volatility Reference:** Low: 15-25% | Medium: 25-40% | High: 40%+")

if __name__ == "__main__":
    main()