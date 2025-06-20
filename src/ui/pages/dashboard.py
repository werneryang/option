"""
Dashboard Page

Main overview page showing key metrics, recent activity,
and quick access to analysis tools.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

def render():
    """Render the dashboard page"""
    
    st.header("📊 Dashboard")
    
    # Get data service and selected symbol
    data_service = st.session_state.get('data_service')
    selected_symbol = st.session_state.get('symbol_selector', 'AAPL')
    
    if not data_service:
        st.error("Data service not available")
        return
    
    # Main metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    # Get current price and basic info
    current_price = data_service.get_current_price(selected_symbol)
    symbol_info = data_service.get_symbol_info(selected_symbol)
    
    with col1:
        if current_price:
            st.metric(
                label=f"{selected_symbol} Price",
                value=f"${current_price:.2f}",
                delta=None  # TODO: Calculate daily change
            )
        else:
            st.metric(label=f"{selected_symbol} Price", value="N/A")
    
    with col2:
        # Get volatility data
        vol_data = data_service.get_volatility_analysis(selected_symbol, [30])
        vol_30d = vol_data.get('30d', 0) * 100 if vol_data else 0
        st.metric(
            label="30-Day Vol",
            value=f"{vol_30d:.1f}%"
        )
    
    with col3:
        # Option chain count
        option_chain = data_service.get_option_chain(selected_symbol)
        option_count = len(option_chain) if option_chain is not None else 0
        st.metric(
            label="Options Available",
            value=option_count
        )
    
    with col4:
        # Data freshness
        data_summary = data_service.get_data_summary()
        st.metric(
            label="Data Files",
            value=data_summary['total_files']
        )
    
    st.markdown("---")
    
    # Price chart and volatility analysis
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📈 {selected_symbol} Price History (30 Days)")
        
        price_history = data_service.get_price_history(selected_symbol, days=30)
        
        if price_history is not None and len(price_history) > 0:
            # Create price chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=price_history['date'],
                y=price_history['close'],
                mode='lines',
                name='Close Price',
                line=dict(color='#1f77b4', width=2)
            ))
            
            fig.update_layout(
                title=f"{selected_symbol} Price Movement",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                height=400,
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No price history available for {selected_symbol}")
    
    with col2:
        st.subheader("📊 Volatility Analysis")
        
        vol_periods = [10, 20, 30, 60]
        vol_analysis = data_service.get_volatility_analysis(selected_symbol, vol_periods)
        
        if vol_analysis:
            vol_df = pd.DataFrame([
                {"Period": f"{period}d", "Volatility": vol_analysis.get(f'{period}d', 0) * 100}
                for period in vol_periods
                if f'{period}d' in vol_analysis
            ])
            
            if not vol_df.empty:
                fig = px.bar(
                    vol_df, 
                    x='Period', 
                    y='Volatility',
                    title="Historical Volatility",
                    color='Volatility',
                    color_continuous_scale='RdYlBu_r'
                )
                fig.update_layout(
                    height=300,
                    showlegend=False,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No volatility data available")
        else:
            st.info("No volatility data available")
    
    st.markdown("---")
    
    # Recent activity and quick actions
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Quick Actions")
        
        # Quick strategy builders - using navigation links instead of buttons
        st.markdown("**Navigate to:**")
        
        col_nav1, col_nav2, col_nav3 = st.columns(3)
        
        with col_nav1:
            if st.button("🎯 Option Chain", use_container_width=True, key="nav_option_chain"):
                st.info("Use the sidebar to navigate to Option Chain page")
        
        with col_nav2:
            if st.button("🏗️ Strategy Builder", use_container_width=True, key="nav_strategy"):
                st.info("Use the sidebar to navigate to Strategy Builder page")
        
        with col_nav3:
            if st.button("📈 Analytics", use_container_width=True, key="nav_analytics"):
                st.info("Use the sidebar to navigate to Analytics page")
        
        # Symbol info card
        st.markdown("### Symbol Information")
        info_data = {
            "Name": symbol_info.get('name', 'N/A'),
            "Sector": symbol_info.get('sector', 'N/A'),
            "Status": "Active" if symbol_info.get('is_active', True) else "Inactive"
        }
        
        for key, value in info_data.items():
            st.write(f"**{key}:** {value}")
    
    with col2:
        st.subheader("💾 Data Summary")
        
        # Data availability summary
        summary = data_service.get_data_summary()
        
        summary_metrics = [
            ("Total Symbols", summary['total_symbols']),
            ("Data Files", summary['total_files']),
            ("Storage Used", f"{summary['total_size_mb']:.1f} MB"),
            ("Available Symbols", len(summary['symbols_with_data']))
        ]
        
        for label, value in summary_metrics:
            st.write(f"**{label}:** {value}")
        
        # Available symbols list
        if summary['symbols_with_data']:
            st.markdown("**Symbols with Data:**")
            symbols_text = ", ".join(summary['symbols_with_data'])
            st.write(symbols_text)
        
        # Performance tip
        with st.expander("💡 Performance Tips"):
            st.markdown("""
            - **Data Loading**: First-time calculations may take longer
            - **Caching**: Results are cached for faster subsequent access  
            - **Refresh**: Use the refresh button if data seems stale
            - **Symbol Selection**: Switch symbols using the sidebar
            """)
    
    # Footer note
    st.markdown("---")
    st.info(
        "💡 **Tip**: This dashboard provides a quick overview. "
        "Use the navigation menu to access detailed analysis tools."
    )