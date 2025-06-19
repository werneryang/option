"""
Analytics Page

Advanced analysis tools including volatility analysis,
backtesting, and comprehensive option analytics.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

def render():
    """Render the analytics page"""
    
    st.header("📈 Advanced Analytics")
    
    # Get data service and selected symbol
    data_service = st.session_state.get('data_service')
    selected_symbol = st.session_state.get('selected_symbol', 'AAPL')
    
    if not data_service:
        st.error("Data service not available")
        return
    
    # Analytics navigation
    analysis_type = st.selectbox(
        "Select Analysis Type:",
        [
            "Volatility Analysis",
            "Historical Performance", 
            "Risk Metrics",
            "Strategy Backtesting"
        ],
        key="analytics_type"
    )
    
    st.markdown("---")
    
    if analysis_type == "Volatility Analysis":
        render_volatility_analysis(data_service, selected_symbol)
    
    elif analysis_type == "Historical Performance":
        render_historical_performance(data_service, selected_symbol)
    
    elif analysis_type == "Risk Metrics":
        render_risk_metrics(data_service, selected_symbol)
    
    elif analysis_type == "Strategy Backtesting":
        render_strategy_backtesting(data_service, selected_symbol)

def render_volatility_analysis(data_service, symbol: str):
    """Render volatility analysis section"""
    
    st.subheader("📊 Volatility Analysis")
    
    # Get price history
    price_history = data_service.get_price_history(symbol, days=252)  # ~1 year
    
    if price_history is None or len(price_history) < 30:
        st.warning(f"Insufficient price data for {symbol}")
        return
    
    # Volatility periods
    col1, col2 = st.columns(2)
    
    with col1:
        periods = st.multiselect(
            "Volatility Periods (days)",
            [10, 20, 30, 60, 90, 180, 252],
            default=[20, 60, 252],
            key="vol_periods"
        )
    
    with col2:
        lookback_days = st.slider(
            "Historical Lookback (days)",
            min_value=60,
            max_value=365,
            value=180,
            key="vol_lookback"
        )
    
    if not periods:
        st.warning("Please select at least one volatility period")
        return
    
    # Calculate volatility for different periods
    vol_data = data_service.get_volatility_analysis(symbol, periods)
    
    if not vol_data:
        st.error("Failed to calculate volatility")
        return
    
    # Current volatility metrics
    st.subheader("Current Volatility Levels")
    
    cols = st.columns(len(periods))
    for i, period in enumerate(periods):
        with cols[i]:
            vol_value = vol_data.get(f'{period}d', 0) * 100
            st.metric(f"{period}d Vol", f"{vol_value:.1f}%")
    
    # Volatility chart over time
    st.subheader("Historical Volatility Trend")
    
    # Calculate rolling volatility
    if len(price_history) >= max(periods) + 20:
        price_history['returns'] = price_history['close'].pct_change()
        
        fig = go.Figure()
        
        for period in periods:
            if len(price_history) >= period + 10:
                rolling_vol = price_history['returns'].rolling(window=period).std() * np.sqrt(252) * 100
                
                fig.add_trace(go.Scatter(
                    x=price_history['date'],
                    y=rolling_vol,
                    mode='lines',
                    name=f'{period}d Vol',
                    line=dict(width=2)
                ))
        
        fig.update_layout(
            title="Rolling Historical Volatility",
            xaxis_title="Date",
            yaxis_title="Volatility (%)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Volatility distribution
    if len(price_history) >= 60:
        st.subheader("Volatility Distribution")
        
        returns = price_history['close'].pct_change().dropna()
        daily_vol = returns.std() * np.sqrt(252) * 100
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Returns histogram
            fig_hist = px.histogram(
                x=returns * 100,
                nbins=50,
                title="Daily Returns Distribution",
                labels={'x': 'Daily Return (%)', 'y': 'Frequency'}
            )
            fig_hist.update_layout(height=300)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Volatility percentiles
            vol_percentiles = {
                "Current Vol": daily_vol,
                "25th Percentile": np.percentile(returns.abs() * np.sqrt(252) * 100, 25),
                "50th Percentile": np.percentile(returns.abs() * np.sqrt(252) * 100, 50),
                "75th Percentile": np.percentile(returns.abs() * np.sqrt(252) * 100, 75),
                "95th Percentile": np.percentile(returns.abs() * np.sqrt(252) * 100, 95)
            }
            
            vol_df = pd.DataFrame(list(vol_percentiles.items()), columns=['Metric', 'Value'])
            vol_df['Value'] = vol_df['Value'].round(2)
            
            st.dataframe(vol_df, use_container_width=True)

def render_historical_performance(data_service, symbol: str):
    """Render historical performance analysis"""
    
    st.subheader("📊 Historical Performance")
    
    # Time period selection
    col1, col2 = st.columns(2)
    
    with col1:
        lookback_period = st.selectbox(
            "Analysis Period",
            ["1 Month", "3 Months", "6 Months", "1 Year"],
            index=2,
            key="perf_period"
        )
    
    with col2:
        metrics_type = st.selectbox(
            "Metrics Type",
            ["Returns", "Risk-Adjusted", "Drawdown"],
            key="metrics_type"
        )
    
    # Get period in days
    period_map = {
        "1 Month": 30,
        "3 Months": 90, 
        "6 Months": 180,
        "1 Year": 365
    }
    days = period_map[lookback_period]
    
    # Get price data
    price_history = data_service.get_price_history(symbol, days)
    
    if price_history is None or len(price_history) < 30:
        st.warning(f"Insufficient data for {symbol}")
        return
    
    # Calculate performance metrics
    prices = price_history['close']
    returns = prices.pct_change().dropna()
    
    # Basic metrics
    total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
    annualized_return = ((prices.iloc[-1] / prices.iloc[0]) ** (252/len(prices)) - 1) * 100
    volatility = returns.std() * np.sqrt(252) * 100
    sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
    
    # Drawdown calculation
    cumulative_returns = (1 + returns).cumprod()
    running_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Return", f"{total_return:.2f}%")
    with col2:
        st.metric("Annualized Return", f"{annualized_return:.2f}%")
    with col3:
        st.metric("Volatility", f"{volatility:.2f}%")
    with col4:
        st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
    
    # Performance chart
    fig = go.Figure()
    
    if metrics_type == "Returns":
        cumulative_pct = (cumulative_returns - 1) * 100
        fig.add_trace(go.Scatter(
            x=price_history['date'][1:],
            y=cumulative_pct,
            mode='lines',
            name='Cumulative Return',
            line=dict(color='#1f77b4', width=2)
        ))
        fig.update_layout(
            title="Cumulative Returns",
            yaxis_title="Return (%)"
        )
    
    elif metrics_type == "Drawdown":
        fig.add_trace(go.Scatter(
            x=price_history['date'][1:],
            y=drawdown,
            mode='lines',
            name='Drawdown',
            line=dict(color='red', width=2),
            fill='tonexty',
            fillcolor='rgba(255, 0, 0, 0.1)'
        ))
        fig.update_layout(
            title="Drawdown Analysis",
            yaxis_title="Drawdown (%)"
        )
    
    fig.update_layout(
        height=400,
        xaxis_title="Date",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Additional statistics
    with st.expander("📊 Detailed Statistics"):
        stats_data = {
            "Metric": [
                "Total Return", "Annualized Return", "Volatility", 
                "Sharpe Ratio", "Max Drawdown", "Calmar Ratio",
                "Best Day", "Worst Day", "Positive Days"
            ],
            "Value": [
                f"{total_return:.2f}%",
                f"{annualized_return:.2f}%", 
                f"{volatility:.2f}%",
                f"{sharpe_ratio:.2f}",
                f"{max_drawdown:.2f}%",
                f"{annualized_return / abs(max_drawdown):.2f}" if max_drawdown != 0 else "N/A",
                f"{returns.max() * 100:.2f}%",
                f"{returns.min() * 100:.2f}%",
                f"{(returns > 0).sum()} / {len(returns)} ({(returns > 0).mean() * 100:.1f}%)"
            ]
        }
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True)

def render_risk_metrics(data_service, symbol: str):
    """Render risk metrics analysis"""
    
    st.subheader("⚠️ Risk Analysis")
    
    # Get current portfolio/position (placeholder)
    st.info("Risk analysis for current positions (feature in development)")
    
    # Value at Risk calculation
    price_history = data_service.get_price_history(symbol, 252)
    
    if price_history is None or len(price_history) < 60:
        st.warning("Insufficient data for risk analysis")
        return
    
    returns = price_history['close'].pct_change().dropna()
    
    # VaR calculations
    confidence_levels = [0.95, 0.99]
    var_results = {}
    
    for conf in confidence_levels:
        var_pct = np.percentile(returns, (1-conf) * 100) * 100
        var_results[f"VaR {conf*100:.0f}%"] = f"{var_pct:.2f}%"
    
    # Display VaR
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("VaR 95%", var_results["VaR 95%"])
    with col2:
        st.metric("VaR 99%", var_results["VaR 99%"])
    
    # Risk distribution chart
    fig = px.histogram(
        x=returns * 100,
        nbins=50,
        title="Return Distribution with VaR Levels"
    )
    
    # Add VaR lines
    for conf in confidence_levels:
        var_val = np.percentile(returns, (1-conf) * 100) * 100
        fig.add_vline(x=var_val, line_dash="dash", 
                     annotation_text=f"VaR {conf*100:.0f}%")
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def render_strategy_backtesting(data_service, symbol: str):
    """Render strategy backtesting section"""
    
    st.subheader("🔄 Strategy Backtesting")
    
    st.info("Advanced backtesting engine (feature in development)")
    
    # Simple backtesting preview
    current_strategy = st.session_state.get('current_strategy')
    
    if current_strategy:
        st.success(f"Strategy loaded: {current_strategy.name}")
        
        # Backtesting parameters
        col1, col2 = st.columns(2)
        
        with col1:
            backtest_days = st.slider(
                "Backtest Period (days)",
                min_value=30,
                max_value=365,
                value=90,
                key="backtest_days"
            )
        
        with col2:
            rebalance_freq = st.selectbox(
                "Rebalance Frequency",
                ["Daily", "Weekly", "Monthly"],
                key="rebalance_freq"
            )
        
        if st.button("🚀 Run Backtest"):
            with st.spinner("Running backtest..."):
                # Placeholder for backtesting results
                st.success("Backtest completed!")
                
                # Mock results
                st.metric("Total Return", "12.5%")
                st.metric("Sharpe Ratio", "1.8")
                st.metric("Max Drawdown", "-5.2%")
    else:
        st.info("Build a strategy first to enable backtesting")
        
        if st.button("🏗️ Go to Strategy Builder"):
            st.session_state.page_selector = "Strategy Builder"
            st.rerun()