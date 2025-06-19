#!/usr/bin/env python3
"""
Simplified Options Analysis Platform - Personal Use

Single-page Streamlit app with essential functionality
for quick options analysis and strategy evaluation.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ui.services.data_service import DataService
from src.analytics.black_scholes import BlackScholesCalculator

# Page configuration
st.set_page_config(
    page_title="Options Analysis",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'data_service' not in st.session_state:
    st.session_state.data_service = DataService()

def main():
    st.title("📈 Options Analysis Platform")
    
    data_service = st.session_state.data_service
    
    # Quick controls in columns
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        symbols = data_service.get_available_symbols() or ['AAPL', 'SPY', 'TSLA']
        symbol = st.selectbox("Symbol", symbols, key="symbol")
    
    with col2:
        analysis_type = st.selectbox("Analysis", ["Greeks", "Strategy", "Volatility"], key="analysis")
    
    with col3:
        risk_free_rate = st.number_input("Risk-Free Rate", 0.0, 0.1, 0.05, 0.001, format="%.3f")
    
    with col4:
        if st.button("🔄 Refresh"):
            data_service.clear_cache()
            st.rerun()
    
    st.markdown("---")
    
    # Main analysis area
    if analysis_type == "Greeks":
        render_greeks_analysis(data_service, symbol, risk_free_rate)
    elif analysis_type == "Strategy":
        render_strategy_analysis(data_service, symbol, risk_free_rate)
    elif analysis_type == "Volatility":
        render_volatility_analysis(data_service, symbol)

def render_greeks_analysis(data_service, symbol, risk_free_rate):
    st.subheader("🔢 Greeks Calculator")
    
    # Simple input controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        current_price = st.number_input("Current Price", 50.0, 500.0, 150.0, 1.0)
    with col2:
        strike = st.number_input("Strike", 50.0, 500.0, 155.0, 1.0)
    with col3:
        days_to_expiry = st.number_input("Days to Expiry", 1, 365, 30, 1)
    with col4:
        volatility = st.number_input("Volatility", 0.05, 2.0, 0.25, 0.01)
    
    time_to_expiry = days_to_expiry / 365.0
    
    # Calculate and display Greeks
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📞 CALL OPTIONS**")
        call_price = BlackScholesCalculator.option_price(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'call')
        call_delta = BlackScholesCalculator.delta(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'call')
        call_gamma = BlackScholesCalculator.gamma(current_price, strike, time_to_expiry, risk_free_rate, volatility)
        call_theta = BlackScholesCalculator.theta(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'call')
        call_vega = BlackScholesCalculator.vega(current_price, strike, time_to_expiry, risk_free_rate, volatility)
        
        metrics_data = {
            "Metric": ["Price", "Delta", "Gamma", "Theta", "Vega"],
            "Value": [f"${call_price:.2f}", f"{call_delta:.4f}", f"{call_gamma:.4f}", f"{call_theta:.4f}", f"{call_vega:.4f}"]
        }
        st.dataframe(pd.DataFrame(metrics_data), hide_index=True, use_container_width=True)
    
    with col2:
        st.markdown("**📈 PUT OPTIONS**")
        put_price = BlackScholesCalculator.option_price(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'put')
        put_delta = BlackScholesCalculator.delta(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'put')
        put_theta = BlackScholesCalculator.theta(current_price, strike, time_to_expiry, risk_free_rate, volatility, 'put')
        
        metrics_data = {
            "Metric": ["Price", "Delta", "Gamma", "Theta", "Vega"],
            "Value": [f"${put_price:.2f}", f"{put_delta:.4f}", f"{call_gamma:.4f}", f"{put_theta:.4f}", f"{call_vega:.4f}"]
        }
        st.dataframe(pd.DataFrame(metrics_data), hide_index=True, use_container_width=True)
    
    # Quick visualization
    strikes = np.linspace(current_price * 0.8, current_price * 1.2, 20)
    call_deltas = [BlackScholesCalculator.delta(current_price, s, time_to_expiry, risk_free_rate, volatility, 'call') for s in strikes]
    put_deltas = [BlackScholesCalculator.delta(current_price, s, time_to_expiry, risk_free_rate, volatility, 'put') for s in strikes]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=strikes, y=call_deltas, name='Call Delta', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=strikes, y=put_deltas, name='Put Delta', line=dict(color='red')))
    fig.add_vline(x=current_price, line_dash="dash", annotation_text="Current Price")
    fig.update_layout(title="Delta by Strike", xaxis_title="Strike", yaxis_title="Delta", height=300)
    st.plotly_chart(fig, use_container_width=True)

def render_strategy_analysis(data_service, symbol, risk_free_rate):
    st.subheader("🏗️ Strategy Builder")
    
    # Strategy selection
    col1, col2 = st.columns([1, 2])
    
    with col1:
        strategy_type = st.selectbox("Strategy", [
            "long_call", "straddle", "strangle", "iron_condor"
        ], format_func=lambda x: x.replace('_', ' ').title())
        
        current_price = st.number_input("Current Price", 50.0, 500.0, 150.0, 1.0, key="strat_price")
        days_to_expiry = st.number_input("Days to Expiry", 1, 365, 30, 1, key="strat_days")
        volatility = st.number_input("Volatility", 0.05, 2.0, 0.25, 0.01, key="strat_vol")
    
    with col2:
        # Strategy parameters based on type
        if strategy_type == "long_call":
            strike = st.number_input("Strike", 50.0, 500.0, current_price * 1.05, 1.0, key="call_strike")
            premium = st.number_input("Premium", 0.1, 50.0, 5.0, 0.1, key="call_premium")
            params = {"strike": strike, "expiration": date.today() + timedelta(days=days_to_expiry), "premium": premium}
        
        elif strategy_type == "straddle":
            strike = st.number_input("Strike", 50.0, 500.0, current_price, 1.0, key="straddle_strike")
            call_premium = st.number_input("Call Premium", 0.1, 50.0, 5.0, 0.1, key="straddle_call")
            put_premium = st.number_input("Put Premium", 0.1, 50.0, 5.0, 0.1, key="straddle_put")
            params = {
                "strike": strike, 
                "expiration": date.today() + timedelta(days=days_to_expiry),
                "call_premium": call_premium,
                "put_premium": put_premium
            }
        
        elif strategy_type == "strangle":
            put_strike = st.number_input("Put Strike", 50.0, 500.0, current_price * 0.95, 1.0, key="strangle_put")
            call_strike = st.number_input("Call Strike", 50.0, 500.0, current_price * 1.05, 1.0, key="strangle_call")
            params = {
                "put_strike": put_strike,
                "call_strike": call_strike,
                "expiration": date.today() + timedelta(days=days_to_expiry)
            }
        
        else:  # iron_condor
            st.info("Iron Condor - using default strikes")
            params = {
                "put_long_strike": current_price * 0.9,
                "put_short_strike": current_price * 0.95,
                "call_short_strike": current_price * 1.05,
                "call_long_strike": current_price * 1.1,
                "expiration": date.today() + timedelta(days=days_to_expiry)
            }
    
    # Build and analyze strategy
    try:
        strategy = data_service.build_strategy(strategy_type, params)
        if strategy:
            st.success(f"✅ {strategy.name}")
            
            # Calculate P&L
            price_range = (current_price * 0.7, current_price * 1.3)
            time_to_expiry = days_to_expiry / 365.0
            
            pnl_result = data_service.calculate_strategy_pnl(strategy, current_price, price_range, time_to_expiry)
            
            if pnl_result:
                # P&L Chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=pnl_result.underlying_prices,
                    y=pnl_result.pnl_values,
                    mode='lines',
                    fill='tonexty',
                    name='P&L'
                ))
                fig.add_vline(x=current_price, line_dash="dash", annotation_text="Current")
                fig.add_hline(y=0, line_color="black")
                fig.update_layout(title="Strategy P&L", xaxis_title="Price", yaxis_title="P&L", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Key metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Max Profit", f"${pnl_result.max_profit:.2f}")
                with col2:
                    st.metric("Max Loss", f"${pnl_result.max_loss:.2f}")
                with col3:
                    st.metric("Breakevens", len(pnl_result.breakeven_points))
        else:
            st.error("Failed to build strategy")
    except Exception as e:
        st.error(f"Error: {e}")

def render_volatility_analysis(data_service, symbol):
    st.subheader("📊 Volatility Analysis")
    
    # Simple volatility display
    periods = [20, 60, 252]
    vol_data = data_service.get_volatility_analysis(symbol, periods)
    
    if vol_data:
        # Display current volatility levels
        cols = st.columns(len(periods))
        for i, period in enumerate(periods):
            with cols[i]:
                vol_value = vol_data.get(f'{period}d', 0) * 100
                st.metric(f"{period}d Vol", f"{vol_value:.1f}%")
        
        # Quick price chart if data available
        price_history = data_service.get_price_history(symbol, 60)
        if price_history is not None and len(price_history) > 10:
            fig = px.line(price_history, x='date', y='close', title=f"{symbol} Price (60 days)")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No price history for {symbol}")
    else:
        st.warning(f"No volatility data available for {symbol}")
    
    # Manual volatility calculator
    st.markdown("**Manual Vol Calculator**")
    col1, col2 = st.columns(2)
    with col1:
        high = st.number_input("High", 0.0, 1000.0, 155.0, 0.01, key="vol_high")
        low = st.number_input("Low", 0.0, 1000.0, 145.0, 0.01, key="vol_low")
    with col2:
        close_prev = st.number_input("Previous Close", 0.0, 1000.0, 148.0, 0.01, key="vol_prev")
        close_curr = st.number_input("Current Close", 0.0, 1000.0, 152.0, 0.01, key="vol_curr")
    
    # Simple return-based volatility
    if close_prev > 0:
        daily_return = (close_curr - close_prev) / close_prev
        annualized_vol = abs(daily_return) * np.sqrt(252) * 100
        st.metric("Estimated Annualized Vol", f"{annualized_vol:.1f}%")

if __name__ == "__main__":
    main()