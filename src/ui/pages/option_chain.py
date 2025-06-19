"""
Option Chain Page

Interactive option chain display with Greeks, filtering,
and detailed option analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

def render():
    """Render the option chain page"""
    
    st.header("🔗 Option Chain Analysis")
    
    # Get data service and selected symbol
    data_service = st.session_state.get('data_service')
    selected_symbol = st.session_state.get('symbol_selector', 'AAPL')
    risk_free_rate = st.session_state.get('risk_free_rate_slider', 5.0) / 100.0
    
    if not data_service:
        st.error("Data service not available")
        return
    
    # Get current price
    current_price = data_service.get_current_price(selected_symbol)
    if not current_price:
        st.warning(f"No price data available for {selected_symbol}")
        return
    
    # Control panel
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Price", f"${current_price:.2f}")
    
    with col2:
        # Strike range filter
        strike_range = st.slider(
            "Strike Range (% of current price)",
            min_value=50,
            max_value=150,
            value=(80, 120),
            step=5,
            format="%d%%"
        )
        min_strike = current_price * strike_range[0] / 100
        max_strike = current_price * strike_range[1] / 100
    
    with col3:
        # Option type filter
        option_types = st.multiselect(
            "Option Types",
            ["C", "P"],
            default=["C", "P"],
            format_func=lambda x: "Calls" if x == "C" else "Puts"
        )
    
    # Load option chain
    option_chain = data_service.get_option_chain(selected_symbol)
    
    if option_chain is None or len(option_chain) == 0:
        st.warning(f"No option chain data available for {selected_symbol}")
        st.info("💡 Try downloading data using: `python main.py download`")
        return
    
    # Filter option chain
    filtered_chain = option_chain[
        (option_chain['strike'] >= min_strike) &
        (option_chain['strike'] <= max_strike) &
        (option_chain['option_type'].isin(option_types))
    ].copy()
    
    if len(filtered_chain) == 0:
        st.warning("No options match the current filters")
        return
    
    # Calculate Greeks
    with st.spinner("Calculating Greeks..."):
        greeks_df = data_service.calculate_greeks(
            selected_symbol, filtered_chain, current_price, risk_free_rate
        )
    
    # Merge option data with Greeks
    if not greeks_df.empty:
        display_data = filtered_chain.merge(
            greeks_df, 
            on=['strike', 'option_type'], 
            how='left'
        )
    else:
        display_data = filtered_chain
        st.warning("Greeks calculation failed - showing basic option data only")
    
    # Display options
    st.subheader("📊 Option Chain Data")
    
    # Format display columns
    display_columns = ['strike', 'option_type', 'bid', 'ask', 'last', 'volume']
    greek_columns = ['delta', 'gamma', 'theta', 'vega', 'rho']
    
    # Add Greeks columns if available
    available_greeks = [col for col in greek_columns if col in display_data.columns]
    display_columns.extend(available_greeks)
    
    # Format the dataframe for display
    formatted_data = display_data[display_columns].copy()
    
    # Round numeric columns
    numeric_columns = ['bid', 'ask', 'last'] + available_greeks
    for col in numeric_columns:
        if col in formatted_data.columns:
            formatted_data[col] = formatted_data[col].round(4)
    
    # Color coding based on moneyness
    def highlight_moneyness(row):
        strike = row['strike']
        if abs(strike - current_price) / current_price < 0.02:  # Within 2%
            return ['background-color: #ffffcc'] * len(row)  # Light yellow for ATM
        elif (row['option_type'] == 'C' and strike < current_price) or \
             (row['option_type'] == 'P' and strike > current_price):
            return ['background-color: #ccffcc'] * len(row)  # Light green for ITM
        else:
            return ['background-color: #ffcccc'] * len(row)  # Light red for OTM
    
    # Display the styled dataframe
    st.dataframe(
        formatted_data.style.apply(highlight_moneyness, axis=1),
        use_container_width=True,
        height=400
    )
    
    # Legend
    st.markdown("""
    **Color Legend:** 
    🟡 **Yellow** = At-the-money (within 2%) | 
    🟢 **Green** = In-the-money | 
    🔴 **Red** = Out-of-the-money
    """)
    
    # Visualization section
    if not greeks_df.empty:
        st.markdown("---")
        st.subheader("📈 Greeks Visualization")
        
        # Greeks charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Delta chart
            fig_delta = px.scatter(
                greeks_df,
                x='strike',
                y='delta',
                color='option_type',
                title="Delta by Strike",
                color_discrete_map={'C': '#1f77b4', 'P': '#ff7f0e'}
            )
            fig_delta.add_vline(x=current_price, line_dash="dash", annotation_text="Current Price")
            fig_delta.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_delta, use_container_width=True)
        
        with col2:
            # Gamma chart
            fig_gamma = px.scatter(
                greeks_df,
                x='strike',
                y='gamma',
                color='option_type',
                title="Gamma by Strike",
                color_discrete_map={'C': '#1f77b4', 'P': '#ff7f0e'}
            )
            fig_gamma.add_vline(x=current_price, line_dash="dash", annotation_text="Current Price")
            fig_gamma.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_gamma, use_container_width=True)
        
        # Additional Greeks
        col3, col4 = st.columns(2)
        
        with col3:
            # Theta chart
            fig_theta = px.scatter(
                greeks_df,
                x='strike',
                y='theta',
                color='option_type',
                title="Theta by Strike",
                color_discrete_map={'C': '#1f77b4', 'P': '#ff7f0e'}
            )
            fig_theta.add_vline(x=current_price, line_dash="dash", annotation_text="Current Price")
            fig_theta.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_theta, use_container_width=True)
        
        with col4:
            # Vega chart
            fig_vega = px.scatter(
                greeks_df,
                x='strike',
                y='vega',
                color='option_type',
                title="Vega by Strike",
                color_discrete_map={'C': '#1f77b4', 'P': '#ff7f0e'}
            )
            fig_vega.add_vline(x=current_price, line_dash="dash", annotation_text="Current Price")
            fig_vega.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_vega, use_container_width=True)
    
    # Summary statistics
    st.markdown("---")
    st.subheader("📋 Chain Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        call_count = len(filtered_chain[filtered_chain['option_type'] == 'C'])
        put_count = len(filtered_chain[filtered_chain['option_type'] == 'P'])
        st.metric("Call Options", call_count)
        st.metric("Put Options", put_count)
    
    with col2:
        if 'volume' in filtered_chain.columns:
            total_volume = filtered_chain['volume'].sum()
            avg_volume = filtered_chain['volume'].mean()
            st.metric("Total Volume", f"{total_volume:,.0f}")
            st.metric("Avg Volume", f"{avg_volume:.0f}")
    
    with col3:
        strike_min = filtered_chain['strike'].min()
        strike_max = filtered_chain['strike'].max()
        st.metric("Strike Range", f"${strike_min:.0f} - ${strike_max:.0f}")
        
        if 'expiration' in filtered_chain.columns:
            exp_dates = filtered_chain['expiration'].nunique()
            st.metric("Expiration Dates", exp_dates)
    
    # Export functionality
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("📥 Export Data", use_container_width=True):
            csv_data = formatted_data.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"{selected_symbol}_option_chain.csv",
                mime="text/csv",
                use_container_width=True
            )