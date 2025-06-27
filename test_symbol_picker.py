#!/usr/bin/env python3
"""
Test script to debug symbol picker issue
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.ui.services.data_service import DataService
from src.utils.config import config

st.title("🔍 Symbol Picker Debug Test")

st.write("Testing symbol loading functionality...")

try:
    # Test DataService creation
    st.write("1. Creating DataService...")
    data_service = DataService()
    st.success("✅ DataService created successfully")
    
    # Test get_available_symbols
    st.write("2. Getting available symbols...")
    symbols = data_service.get_available_symbols()
    st.success(f"✅ Available symbols: {symbols}")
    st.write(f"Number of symbols: {len(symbols)}")
    
    # Test selectbox with these symbols
    st.write("3. Testing selectbox...")
    selected_symbol = st.selectbox(
        "Select Symbol (Test):",
        symbols,
        key="test_symbol_selector"
    )
    st.success(f"✅ Selected symbol: {selected_symbol}")
    
    # Test database
    st.write("4. Checking database...")
    db_symbols = data_service.db.get_symbols()
    st.write(f"Database symbols: {[s.symbol for s in db_symbols]}")
    st.write(f"Active database symbols: {[s.symbol for s in db_symbols if s.is_active]}")
    
    # Test storage
    st.write("5. Checking storage...")
    storage_symbols = data_service.storage.get_symbols_with_data()
    st.write(f"Storage symbols: {storage_symbols}")
    
    # Test data paths
    st.write("6. Checking data paths...")
    st.write(f"Processed data path: {config.processed_data_path}")
    st.write(f"Path exists: {config.processed_data_path.exists()}")
    
    if config.processed_data_path.exists():
        import os
        dirs = [d for d in os.listdir(config.processed_data_path) 
                if os.path.isdir(config.processed_data_path / d)]
        st.write(f"Directories: {dirs}")
    
    # Test symbol info for selected symbol
    if selected_symbol:
        st.write("7. Testing symbol info...")
        symbol_info = data_service.get_symbol_info(selected_symbol)
        st.write(f"Symbol info: {symbol_info}")
        
        current_price = data_service.get_current_price(selected_symbol)
        st.write(f"Current price: {current_price}")

except Exception as e:
    st.error(f"❌ Error: {e}")
    import traceback
    st.text(traceback.format_exc())

st.write("---")
st.write("If you can see symbols in the selectbox above, then the issue is elsewhere.")