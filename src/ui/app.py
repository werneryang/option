#!/usr/bin/env python3
"""
Options Analysis Platform - Local Desktop Application

Local historical data analysis platform for options research and education.
Provides comprehensive analytics, strategy building, and backtesting capabilities
for learning and developing options trading strategies.

Focus: Historical data analysis, NOT real-time trading.
"""

import streamlit as st
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.ui.components.sidebar import render_sidebar
from src.ui.pages import dashboard, option_chain, strategy_builder, analytics, data_management
from src.ui.services.data_service import DataService
from src.utils.config import config

# Page configuration
st.set_page_config(
    page_title="Options Analysis Platform - Local Desktop",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        text-align: center;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .stDataFrame {
        border: 1px solid #e6e9ef;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables - only non-widget variables"""
    if 'data_service' not in st.session_state:
        st.session_state.data_service = DataService()
    
    if 'current_strategy' not in st.session_state:
        st.session_state.current_strategy = None

def main():
    """Main application entry point"""
    initialize_session_state()
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>📈 Options Analysis Platform</h1>
        <p style="color: white; text-align: center; margin: 0; font-size: 0.9em;">
            Local Historical Data Analysis • Educational Platform • No Real-time Trading
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render sidebar navigation
    page = render_sidebar()
    
    # Route to appropriate page
    if page == "Dashboard":
        dashboard.render()
    elif page == "Option Chain":
        option_chain.render()
    elif page == "Strategy Builder":
        strategy_builder.render()
    elif page == "Analytics":
        analytics.render()
    elif page == "Data Management":
        data_management.render()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Local Options Analysis Platform | Historical Data Analysis | Educational Use Only"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()