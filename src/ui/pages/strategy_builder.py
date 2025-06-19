"""
Strategy Builder Page

Interactive interface for building and analyzing options strategies
with real-time P&L visualization and risk metrics.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
from typing import Dict, List

def render():
    """Render the strategy builder page"""
    
    st.header("🏗️ Options Strategy Builder")
    
    # Get data service and selected symbol
    data_service = st.session_state.get('data_service')
    selected_symbol = st.session_state.get('selected_symbol', 'AAPL')
    risk_free_rate = st.session_state.get('risk_free_rate', 0.05)
    
    if not data_service:
        st.error("Data service not available")
        return
    
    # Get current price
    current_price = data_service.get_current_price(selected_symbol)
    if not current_price:
        st.warning(f"No price data available for {selected_symbol}")
        return
    
    # Strategy selection
    st.subheader("🎯 Strategy Selection")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        strategy_types = {
            "long_call": "Long Call",
            "long_put": "Long Put", 
            "covered_call": "Covered Call",
            "straddle": "Long Straddle",
            "short_straddle": "Short Straddle",
            "strangle": "Long Strangle",
            "bull_call_spread": "Bull Call Spread",
            "bear_put_spread": "Bear Put Spread",
            "iron_condor": "Iron Condor",
            "butterfly_spread": "Butterfly Spread"
        }
        
        selected_strategy = st.selectbox(
            "Choose Strategy Type:",
            list(strategy_types.keys()),
            format_func=lambda x: strategy_types[x],
            key="strategy_type"
        )
    
    with col2:
        st.metric("Current Price", f"${current_price:.2f}")
        
        # Volatility estimate
        vol_data = data_service.get_volatility_analysis(selected_symbol, [30])
        current_vol = vol_data.get('30d', 0.25) * 100
        st.metric("30d Volatility", f"{current_vol:.1f}%")
    
    st.markdown("---")
    
    # Strategy parameters
    st.subheader("⚙️ Strategy Parameters")
    
    # Get strategy-specific parameters
    strategy_params = get_strategy_parameters(selected_strategy, current_price)
    
    if not strategy_params:
        st.error("Invalid strategy selected")
        return
    
    # Build the strategy
    try:
        strategy = data_service.build_strategy(selected_strategy, strategy_params)
        if not strategy:
            st.error("Failed to build strategy")
            return
    except Exception as e:
        st.error(f"Error building strategy: {e}")
        return
    
    # Store in session state
    st.session_state.current_strategy = strategy
    
    st.markdown("---")
    
    # P&L Analysis
    st.subheader("📈 Profit & Loss Analysis")
    
    # P&L parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        price_range_pct = st.slider(
            "Price Range (%)",
            min_value=10,
            max_value=50,
            value=30,
            step=5,
            help="Range around current price for P&L analysis"
        )
    
    with col2:
        days_to_expiry = st.slider(
            "Days to Expiry",
            min_value=0,
            max_value=365,
            value=30,
            step=1,
            help="Days remaining until expiration"
        )
    
    with col3:
        volatility_input = st.slider(
            "Volatility (%)",
            min_value=5.0,
            max_value=100.0,
            value=current_vol,
            step=1.0,
            help="Implied volatility for calculations"
        ) / 100.0
    
    # Calculate P&L
    price_min = current_price * (1 - price_range_pct/100)
    price_max = current_price * (1 + price_range_pct/100)
    time_to_expiry = days_to_expiry / 365.0
    
    try:
        pnl_result = data_service.calculate_strategy_pnl(
            strategy, current_price, 
            (price_min, price_max), 
            time_to_expiry
        )
        
        if pnl_result:
            # P&L Chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=pnl_result.underlying_prices,
                y=pnl_result.pnl_values,
                mode='lines',
                name='P&L',
                line=dict(color='#1f77b4', width=2),
                fill='tonexty',
                fillcolor='rgba(31, 119, 180, 0.1)'
            ))
            
            # Add breakeven lines
            for breakeven in pnl_result.breakeven_points:
                fig.add_vline(
                    x=breakeven, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text=f"BE: ${breakeven:.2f}"
                )
            
            # Add current price line
            fig.add_vline(
                x=current_price,
                line_dash="dot",
                line_color="green", 
                annotation_text=f"Current: ${current_price:.2f}"
            )
            
            # Add zero line
            fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
            
            fig.update_layout(
                title=f"{strategy_types[selected_strategy]} P&L Diagram",
                xaxis_title="Underlying Price ($)",
                yaxis_title="Profit/Loss ($)",
                height=500,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # P&L Metrics
            st.subheader("📊 Strategy Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Max Profit", f"${pnl_result.max_profit:.2f}")
            
            with col2:
                st.metric("Max Loss", f"${pnl_result.max_loss:.2f}")
            
            with col3:
                profit_range = pnl_result.profit_range
                if profit_range[0] != float('inf'):
                    range_text = f"${profit_range[0]:.2f} - ${profit_range[1]:.2f}"
                else:
                    range_text = "None"
                st.metric("Profit Range", range_text)
            
            with col4:
                st.metric("Breakeven Points", len(pnl_result.breakeven_points))
            
            # Breakeven details
            if pnl_result.breakeven_points:
                st.markdown("**Breakeven Prices:**")
                breakeven_text = ", ".join([f"${be:.2f}" for be in pnl_result.breakeven_points])
                st.write(breakeven_text)
        
        else:
            st.error("Failed to calculate P&L")
            
    except Exception as e:
        st.error(f"Error calculating P&L: {e}")
    
    st.markdown("---")
    
    # Strategy Details
    st.subheader("📋 Strategy Details")
    
    # Display strategy legs
    if hasattr(strategy, 'option_legs') and strategy.option_legs:
        legs_data = []
        for i, leg in enumerate(strategy.option_legs):
            legs_data.append({
                "Leg": i + 1,
                "Type": f"{leg.position_type.value.title()} {leg.option_type.value.upper()}",
                "Strike": f"${leg.strike:.2f}",
                "Quantity": leg.quantity,
                "Premium": f"${leg.premium:.2f}" if leg.premium else "N/A",
                "Expiration": leg.expiration.strftime("%Y-%m-%d")
            })
        
        legs_df = pd.DataFrame(legs_data)
        st.dataframe(legs_df, use_container_width=True)
    
    # Stock legs if any
    if hasattr(strategy, 'stock_legs') and strategy.stock_legs:
        st.markdown("**Stock Positions:**")
        for leg in strategy.stock_legs:
            st.write(f"• {leg.position_type.value.title()} {leg.quantity} shares at ${leg.entry_price:.2f}")
    
    # Export strategy
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("💾 Save Strategy", use_container_width=True):
            # TODO: Implement strategy saving
            st.success("Strategy saved! (Feature coming soon)")
    
    # Risk Analysis
    with st.expander("⚠️ Risk Analysis"):
        st.markdown(f"""
        **Strategy**: {strategy_types[selected_strategy]}
        
        **Risk Considerations:**
        - **Maximum Risk**: ${abs(pnl_result.max_loss):.2f} if P&L calculated
        - **Time Decay**: Options lose value as expiration approaches
        - **Volatility Risk**: Changes in implied volatility affect option prices
        - **Assignment Risk**: Short options may be assigned early
        
        **Market Outlook Required:**
        - Check strategy description for directional bias
        - Consider current market conditions and volatility environment
        """)

def get_strategy_parameters(strategy_type: str, current_price: float) -> Dict:
    """Get parameters for the selected strategy type"""
    
    col1, col2, col3 = st.columns(3)
    
    # Common parameters
    with col1:
        expiration_days = st.slider(
            "Days to Expiration",
            min_value=1,
            max_value=365,
            value=30,
            key="exp_days"
        )
        expiration = date.today() + timedelta(days=expiration_days)
    
    params = {"expiration": expiration}
    
    if strategy_type == "long_call":
        with col2:
            strike = st.number_input(
                "Strike Price",
                min_value=current_price * 0.5,
                max_value=current_price * 2.0,
                value=current_price * 1.05,
                step=1.0,
                key="call_strike"
            )
        with col3:
            premium = st.number_input(
                "Premium",
                min_value=0.01,
                max_value=current_price,
                value=5.0,
                step=0.01,
                key="call_premium"
            )
        params.update({"strike": strike, "premium": premium})
    
    elif strategy_type == "straddle":
        with col2:
            strike = st.number_input(
                "Strike Price",
                min_value=current_price * 0.8,
                max_value=current_price * 1.2,
                value=current_price,
                step=1.0,
                key="straddle_strike"
            )
        with col3:
            call_premium = st.number_input(
                "Call Premium",
                min_value=0.01,
                value=5.0,
                step=0.01,
                key="straddle_call_premium"
            )
            put_premium = st.number_input(
                "Put Premium", 
                min_value=0.01,
                value=5.0,
                step=0.01,
                key="straddle_put_premium"
            )
        params.update({
            "strike": strike,
            "call_premium": call_premium,
            "put_premium": put_premium
        })
    
    elif strategy_type == "strangle":
        with col2:
            put_strike = st.number_input(
                "Put Strike",
                min_value=current_price * 0.5,
                max_value=current_price * 0.98,
                value=current_price * 0.95,
                step=1.0,
                key="strangle_put_strike"
            )
            call_strike = st.number_input(
                "Call Strike",
                min_value=current_price * 1.02,
                max_value=current_price * 2.0,
                value=current_price * 1.05,
                step=1.0,
                key="strangle_call_strike"
            )
        with col3:
            call_premium = st.number_input(
                "Call Premium",
                min_value=0.01,
                value=3.0,
                step=0.01,
                key="strangle_call_premium"
            )
            put_premium = st.number_input(
                "Put Premium",
                min_value=0.01,
                value=3.0,
                step=0.01,
                key="strangle_put_premium"
            )
        params.update({
            "put_strike": put_strike,
            "call_strike": call_strike,
            "call_premium": call_premium,
            "put_premium": put_premium
        })
    
    else:
        # For other strategies, use simplified parameters
        with col2:
            strike = st.number_input(
                "Strike Price",
                min_value=current_price * 0.5,
                max_value=current_price * 2.0,
                value=current_price,
                step=1.0,
                key=f"{strategy_type}_strike"
            )
        params.update({"strike": strike})
    
    return params