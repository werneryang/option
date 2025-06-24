"""
Sidebar Navigation Component

Provides navigation menu and global controls for the application.
"""

import streamlit as st
from typing import Dict

def render_sidebar() -> str:
    """Render the sidebar navigation and return selected page"""
    
    with st.sidebar:
        st.markdown("## 🎯 Navigation")
        
        # Page navigation
        pages = {
            "Dashboard": "📊",
            "Option Chain": "🔗",
            "Strategy Builder": "🏗️",
            "Analytics": "📈",
            "Data Management": "💾"
        }
        
        selected_page = st.radio(
            "Choose a page:",
            list(pages.keys()),
            format_func=lambda x: f"{pages[x]} {x}",
            key="page_selector"
        )
        
        st.markdown("---")
        
        # Symbol selection
        st.markdown("## 📌 Symbol Selection")
        
        # Get available symbols from data service
        data_service = st.session_state.get('data_service')
        if data_service:
            available_symbols = data_service.get_available_symbols()
        else:
            available_symbols = ['AAPL', 'SPY', 'TSLA']
        
        # Ensure we have a valid default selection
        default_index = 0
        if 'AAPL' in available_symbols:
            default_index = available_symbols.index('AAPL')
        
        selected_symbol = st.selectbox(
            "Select Symbol:",
            available_symbols,
            index=default_index,
            key="symbol_selector"
        )
        
        # Note: selected_symbol is automatically managed by widget key
        
        # Symbol info
        if data_service and selected_symbol:
            symbol_info = data_service.get_symbol_info(selected_symbol)
            current_price = data_service.get_current_price(selected_symbol)
            
            st.markdown("### Symbol Info")
            st.write(f"**Name:** {symbol_info.get('name', 'N/A')}")
            st.write(f"**Sector:** {symbol_info.get('sector', 'N/A')}")
            if current_price:
                st.write(f"**Current Price:** ${current_price:.2f}")
        
        st.markdown("---")
        
        # Global settings
        st.markdown("## ⚙️ Settings")
        
        risk_free_rate = st.slider(
            "Risk-Free Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=5.0,
            step=0.1,
            format="%.1f%%",
            key="risk_free_rate_slider"
        ) / 100.0
        
        # Data refresh
        if st.button("🔄 Refresh Data", help="Clear cache and reload data"):
            if data_service:
                data_service.clear_cache()
            st.rerun()
        
        st.markdown("---")
        
        # Data status
        st.markdown("## 📊 Data Status")
        
        if data_service:
            data_summary = data_service.get_data_summary()
            st.metric("Symbols", data_summary['total_symbols'])
            st.metric("Data Files", data_summary['total_files'])
            st.metric("Storage", f"{data_summary['total_size_mb']:.1f} MB")
        
        # Help section
        with st.expander("ℹ️ Help"):
            st.markdown("""
            **Navigation:**
            - **Dashboard**: Overview and key metrics
            - **Option Chain**: View and analyze option chains
            - **Strategy Builder**: Create and analyze strategies
            - **Analytics**: Advanced analysis tools
            - **Data Management**: Check data status and manage downloads
            
            **About This Platform:**
            - **Local Desktop Application**: Runs on your computer only
            - **Historical Data Analysis**: Focus on research and backtesting
            - **Educational Tool**: Learn options trading concepts safely
            
            **Tips:**
            - Select different symbols from the dropdown
            - Adjust risk-free rate for calculations
            - Use refresh button if data seems stale
            - Check Data Management for download status
            """)
    
    return selected_page