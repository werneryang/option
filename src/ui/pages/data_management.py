"""
Data Management Page

Provides interface for checking and managing historical data downloads.
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Dict, Any, List

from ...services.async_data_service import async_data_service
from ...utils.trading_calendar import trading_calendar


def get_available_symbols() -> List[str]:
    """Get available symbols from data service or fallback to defaults"""
    data_service = st.session_state.get('data_service')
    if data_service:
        try:
            return data_service.get_available_symbols()
        except Exception:
            pass
    # Fallback to common symbols
    return ['AAPL', 'SPY', 'TSLA', 'QQQ', 'MSFT', 'GOOGL', 'AMZN', 'META']


def render():
    """Render the data management page"""
    
    st.header("📊 Data Management")
    st.markdown("Check and manage historical options data for your symbols.")
    
    # Initialize and clean up session state
    cleanup_old_downloads()
    
    # Create tabs for different functions
    tab1, tab2, tab3 = st.tabs(["🔍 Check Data", "📈 Download Status", "⚙️ Bulk Operations"])
    
    with tab1:
        render_data_checker()
    
    with tab2:
        render_download_status()
    
    with tab3:
        render_bulk_operations()


def cleanup_old_downloads():
    """Clean up old download tasks from session state"""
    if 'active_downloads' not in st.session_state:
        return
    
    # Clean up downloads older than 1 hour that are completed
    current_time = datetime.now()
    old_keys = []
    
    for symbol_key, task_id in st.session_state.active_downloads.items():
        try:
            status = async_data_service.get_download_status(task_id)
            
            # Remove if task not found or very old completed tasks
            if (status.get('status') == 'not_found' or 
                (status.get('status') in ['completed', 'failed', 'error', 'cancelled'] and
                 status.get('completed_at') and
                 (current_time - status['completed_at']).total_seconds() > 3600)):  # 1 hour
                old_keys.append(symbol_key)
        except Exception:
            # Remove if we can't get status
            old_keys.append(symbol_key)
    
    for key in old_keys:
        del st.session_state.active_downloads[key]


def render_data_checker():
    """Render the individual symbol data checker"""
    
    st.subheader("Individual Symbol Check")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Symbol input
        symbol_input = st.text_input(
            "Enter Stock Symbol",
            value="AAPL",
            help="Enter a stock symbol to check its data status",
            key="symbol_input"
        ).upper().strip()
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
        check_button = st.button(
            "🔍 Check Data", 
            type="primary",
            key="check_data_button"
        )
    
    if check_button and symbol_input:
        with st.spinner(f"Checking data for {symbol_input}..."):
            # Perform data freshness check
            freshness_result = async_data_service.check_data_sync(symbol_input)
            
            # Display results
            st.markdown("---")
            st.subheader(f"📋 Data Status for {symbol_input}")
            
            # Status overview
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_color = "🟢" if freshness_result['is_up_to_date'] else "🔴"
                st.metric(
                    "Data Status", 
                    f"{status_color} {'Up to Date' if freshness_result['is_up_to_date'] else 'Needs Update'}"
                )
            
            with col2:
                last_date = freshness_result.get('last_download_date')
                if last_date:
                    try:
                        st.metric("Last Download", last_date.strftime('%Y-%m-%d'))
                    except (AttributeError, ValueError):
                        st.metric("Last Download", str(last_date))
                else:
                    st.metric("Last Download", "Never")
            
            with col3:
                expected_date = freshness_result.get('expected_date')
                if expected_date:
                    try:
                        st.metric("Expected Date", expected_date.strftime('%Y-%m-%d'))
                    except (AttributeError, ValueError):
                        st.metric("Expected Date", str(expected_date))
                else:
                    st.metric("Expected Date", "N/A")
            
            # Details
            st.markdown("### 📝 Details")
            st.info(freshness_result['reason'])
            
            # Trading calendar info
            current_time = datetime.now()
            is_trading_day = trading_calendar.is_trading_day(current_time.date())
            is_before_cutoff = trading_calendar.is_before_market_close_cutoff(current_time)
            
            st.markdown("### 📅 Trading Calendar Info")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Today is Trading Day", "✅ Yes" if is_trading_day else "❌ No")
            
            with col2:
                st.metric("Before 4:30 PM", "✅ Yes" if is_before_cutoff else "❌ No")
                
            with col3:
                cutoff_reason = "Check previous day" if is_before_cutoff else "Check current day"
                st.metric("Logic", cutoff_reason)
            
            # Download action
            if freshness_result['needs_download']:
                st.markdown("### 🔄 Download Required")
                
                download_types = freshness_result.get('download_types_needed', ['historical_options'])
                st.write(f"**Data types to download:** {', '.join(download_types)}")
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button(f"📥 Download Data for {symbol_input}", type="primary", key="download_button"):
                        start_download(symbol_input, download_types)
                
                with col2:
                    force_download = st.checkbox(
                        "Force download (even if data appears current)",
                        key="force_download_checkbox"
                    )
                    if force_download and st.button(f"🔄 Force Download {symbol_input}", key="force_download_button"):
                        start_download(symbol_input, ['historical_options', 'stock_price'], force=True)
            
            # Data summary
            st.markdown("### 📊 Data Summary")
            with st.spinner("Loading data summary..."):
                data_summary = async_data_service.get_data_summary_sync(symbol_input)
                display_data_summary(data_summary)


def start_download(symbol: str, download_types: list, force: bool = False):
    """Start background download and show progress tracking"""
    
    # Initialize session state if needed
    if 'active_downloads' not in st.session_state:
        st.session_state.active_downloads = {}
    
    # Check if there's already an active download for this symbol
    existing_downloads = [key for key in st.session_state.active_downloads.keys() if key.startswith(f"{symbol}_")]
    for key in existing_downloads:
        task_id = st.session_state.active_downloads[key]
        existing_status = async_data_service.get_download_status(task_id)
        if existing_status.get('status') not in ['completed', 'failed', 'error', 'cancelled', 'not_found']:
            st.warning(f"⚠️ Download already in progress for {symbol}. Check Download Status tab.")
            return
    
    # Start the background download
    task_id = async_data_service.start_background_download(symbol, download_types)
    
    # Store task ID with timestamp to avoid conflicts
    st.session_state.active_downloads[f"{symbol}_{task_id}"] = task_id
    
    action_type = "Force download" if force else "Download"
    st.success(f"✅ {action_type} started for {symbol}!")
    st.info(f"📋 Task ID: {task_id}")
    st.info("💡 Check the 'Download Status' tab to monitor progress.")


def show_download_progress():
    """Show progress for active downloads"""
    
    if 'active_downloads' not in st.session_state or not st.session_state.active_downloads:
        st.info("No active downloads.")
        return
    
    # Auto-refresh option
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📊 Active Downloads")
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-refresh", key="auto_refresh_downloads")
        if auto_refresh:
            # Use a more controlled refresh mechanism
            st.info("🔄 Auto-refresh enabled - page will update automatically")
            # Add a small delay to prevent infinite refresh loops
            time.sleep(1)
            st.rerun()
    
    # Get status for all active downloads
    for symbol_key, task_id in st.session_state.active_downloads.items():
        status = async_data_service.get_download_status(task_id)
        
        if status.get('status') == 'not_found':
            continue
        
        # Extract symbol from the key (symbol_taskid format)
        symbol = symbol_key.split('_')[0] if '_' in symbol_key else symbol_key
            
        with st.expander(f"📈 {symbol} - {status.get('status', 'Unknown').title()}", expanded=True):
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                progress = status.get('progress', 0)
                st.progress(progress / 100.0)
                st.text(status.get('message', 'No status message'))
                
            with col2:
                if status.get('status') not in ['completed', 'failed', 'error']:
                    if st.button(f"❌ Cancel", key=f"cancel_{task_id}"):
                        if async_data_service.cancel_download(task_id):
                            st.success("Download cancelled")
                            st.rerun()
                        else:
                            st.error("Could not cancel download")
            
            # Show result if completed
            if status.get('result'):
                result = status['result']
                if result.get('success'):
                    st.success("✅ Download completed successfully!")
                    
                    if result.get('downloads'):
                        for data_type, download_info in result['downloads'].items():
                            if download_info.get('success'):
                                records = download_info.get('records', 0)
                                st.write(f"**{data_type}**: {records:,} records")
                else:
                    st.error("❌ Download failed")
                    if result.get('errors'):
                        for error in result['errors']:
                            st.error(f"Error: {error}")
            
            # Show timing info
            if 'started_at' in status:
                try:
                    st.caption(f"Started: {status['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                except (AttributeError, ValueError):
                    st.caption(f"Started: {status['started_at']}")
            if 'completed_at' in status:
                try:
                    st.caption(f"Completed: {status['completed_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                except (AttributeError, ValueError):
                    st.caption(f"Completed: {status['completed_at']}")
    
    # Cleanup completed downloads button
    if st.button("🧹 Clear Completed Downloads"):
        completed_keys = []
        for symbol_key, task_id in st.session_state.active_downloads.items():
            status = async_data_service.get_download_status(task_id)
            if status.get('status') in ['completed', 'failed', 'error', 'cancelled']:
                completed_keys.append(symbol_key)
        
        for key in completed_keys:
            del st.session_state.active_downloads[key]
        
        if completed_keys:
            st.success(f"Cleared {len(completed_keys)} completed downloads")
            st.rerun()
        else:
            st.info("No completed downloads to clear")


def display_data_summary(summary: Dict[str, Any]):
    """Display data summary information"""
    
    if 'error' in summary:
        st.error(f"Error loading data summary: {summary['error']}")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Historical Options")
        if summary['historical_options']['available']:
            st.success(f"✅ Available ({summary['historical_options']['record_count']:,} records)")
            if summary['historical_options']['last_date']:
                st.write(f"**Last Date:** {summary['historical_options']['last_date']}")
        else:
            st.warning("❌ No data available")
    
    with col2:
        st.markdown("#### 💰 Stock Prices")
        if summary['stock_prices']['available']:
            st.success(f"✅ Available ({summary['stock_prices']['record_count']:,} records)")
            if summary['stock_prices']['last_date']:
                st.write(f"**Last Date:** {summary['stock_prices']['last_date']}")
        else:
            st.warning("❌ No data available")
    
    # Download history
    if summary['recent_downloads']:
        st.markdown("#### 📋 Recent Downloads (Last 30 Days)")
        
        downloads_df = pd.DataFrame([
            {
                'Date': (
                    download['date'].strftime('%Y-%m-%d %H:%M') 
                    if hasattr(download['date'], 'strftime') 
                    else str(download['date'])
                ),
                'Type': download['data_type'],
                'Status': download['status'],
                'Records': download['records_count'] or 0,
                'Error': download['error_message'][:50] + '...' if download['error_message'] and len(download['error_message']) > 50 else download['error_message']
            }
            for download in summary['recent_downloads']
        ])
        
        # Style the dataframe
        def style_status(val):
            if val == 'completed':
                return 'background-color: #d4edda; color: #155724'
            elif val == 'failed':
                return 'background-color: #f8d7da; color: #721c24'
            else:
                return 'background-color: #fff3cd; color: #856404'
        
        styled_df = downloads_df.style.applymap(style_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("No recent downloads found.")


def render_download_status():
    """Render the download status overview"""
    
    st.subheader("Download Status Overview")
    
    # Show active downloads first
    show_download_progress()
    
    st.markdown("---")
    
    # Get available symbols
    available_symbols = get_available_symbols()
    
    # Create a summary table for all symbols
    if st.button("🔄 Refresh Status", key="refresh_status_button"):
        with st.spinner("Loading status for all symbols..."):
            status_data = []
            
            for symbol in available_symbols:
                try:
                    freshness = async_data_service.check_data_sync(symbol)
                    last_date = freshness.get('last_download_date')
                    
                    status_data.append({
                        'Symbol': symbol,
                        'Status': '✅ Up to Date' if freshness['is_up_to_date'] else '❌ Needs Update',
                        'Last Download': last_date.strftime('%Y-%m-%d') if last_date else 'Never',
                        'Expected Date': freshness['expected_date'].strftime('%Y-%m-%d') if freshness['expected_date'] else 'N/A',
                        'Needs Download': freshness['needs_download']
                    })
                except Exception as e:
                    status_data.append({
                        'Symbol': symbol,
                        'Status': f'❌ Error: {str(e)[:30]}...',
                        'Last Download': 'Error',
                        'Expected Date': 'Error',
                        'Needs Download': True
                    })
            
            if status_data:
                df = pd.DataFrame(status_data)
                
                # Color coding
                def highlight_status(row):
                    if 'Up to Date' in row['Status']:
                        return ['background-color: #d4edda'] * len(row)
                    elif 'Needs Update' in row['Status']:
                        return ['background-color: #fff3cd'] * len(row)
                    else:
                        return ['background-color: #f8d7da'] * len(row)
                
                styled_df = df.style.apply(highlight_status, axis=1)
                st.dataframe(styled_df, use_container_width=True)
                
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    up_to_date = len([s for s in status_data if s['Needs Download'] == False])
                    st.metric("Up to Date", up_to_date)
                
                with col2:
                    needs_update = len([s for s in status_data if s['Needs Download'] == True])
                    st.metric("Needs Update", needs_update)
                
                with col3:
                    total_symbols = len(status_data)
                    st.metric("Total Symbols", total_symbols)


def render_bulk_operations():
    """Render bulk operations interface"""
    
    st.subheader("Bulk Operations")
    st.markdown("Perform operations on multiple symbols at once.")
    
    # Get available symbols
    available_symbols = get_available_symbols()
    
    # Symbol selection
    selected_symbols = st.multiselect(
        "Select symbols for bulk operations:",
        available_symbols,
        default=available_symbols[:3] if len(available_symbols) >= 3 else available_symbols,
        key="bulk_symbols_select"
    )
    
    if selected_symbols:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Check All Selected", type="primary", key="bulk_check_button"):
                perform_bulk_check(selected_symbols)
        
        with col2:
            force_all = st.checkbox("Force download for all symbols", key="force_all_checkbox")
            if st.button("📥 Download All", type="secondary", key="bulk_download_button"):
                perform_bulk_download(selected_symbols, force_all)
        
        # Display selected symbols
        st.markdown("### Selected Symbols")
        st.write(", ".join(selected_symbols))
        
        if force_all:
            st.warning("⚠️ This will download data for all selected symbols regardless of current status.")
    
    else:
        st.info("Select one or more symbols to perform bulk operations.")


def perform_bulk_check(symbols: List[str]):
    """Perform bulk data status check"""
    st.markdown("### 📊 Bulk Check Results")
    
    with st.spinner(f"Checking data status for {len(symbols)} symbols..."):
        results = []
        
        for symbol in symbols:
            try:
                freshness = async_data_service.check_data_sync(symbol)
                results.append({
                    'Symbol': symbol,
                    'Status': '✅ Up to Date' if freshness['is_up_to_date'] else '❌ Needs Update',
                    'Last Download': (
                        freshness.get('last_download_date').strftime('%Y-%m-%d') 
                        if freshness.get('last_download_date') and hasattr(freshness.get('last_download_date'), 'strftime')
                        else str(freshness.get('last_download_date')) if freshness.get('last_download_date') else 'Never'
                    ),
                    'Reason': freshness.get('reason', 'Unknown'),
                    'Needs Download': freshness.get('needs_download', False)
                })
            except Exception as e:
                results.append({
                    'Symbol': symbol,
                    'Status': f'❌ Error: {str(e)[:30]}...',
                    'Last Download': 'Error',
                    'Reason': str(e),
                    'Needs Download': True
                })
        
        # Display results
        if results:
            df = pd.DataFrame(results)
            
            # Style the dataframe
            def highlight_status(row):
                if 'Up to Date' in row['Status']:
                    return ['background-color: #d4edda'] * len(row)
                elif 'Needs Update' in row['Status']:
                    return ['background-color: #fff3cd'] * len(row)
                else:
                    return ['background-color: #f8d7da'] * len(row)
            
            styled_df = df.style.apply(highlight_status, axis=1)
            st.dataframe(styled_df, use_container_width=True)
            
            # Summary
            up_to_date = len([r for r in results if not r['Needs Download']])
            needs_update = len([r for r in results if r['Needs Download']])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Up to Date", up_to_date)
            with col2:
                st.metric("Needs Update", needs_update)
            with col3:
                st.metric("Total Checked", len(results))


def perform_bulk_download(symbols: List[str], force: bool = False):
    """Perform bulk data download"""
    st.markdown("### 📥 Bulk Download")
    
    if not force:
        # First check which symbols need updates
        with st.spinner("Checking which symbols need updates..."):
            symbols_to_download = []
            for symbol in symbols:
                try:
                    freshness = async_data_service.check_data_sync(symbol)
                    if freshness.get('needs_download', True):
                        symbols_to_download.append(symbol)
                except Exception:
                    symbols_to_download.append(symbol)  # Download on error
        
        if not symbols_to_download:
            st.success("✅ All selected symbols are up to date!")
            return
            
        st.info(f"📋 {len(symbols_to_download)} out of {len(symbols)} symbols need updates: {', '.join(symbols_to_download)}")
    else:
        symbols_to_download = symbols
        st.info(f"🔄 Force downloading data for all {len(symbols)} symbols...")
    
    # Start downloads
    download_count = 0
    for symbol in symbols_to_download:
        try:
            start_download(symbol, ['historical_options'], force=force)
            download_count += 1
        except Exception as e:
            st.error(f"❌ Failed to start download for {symbol}: {str(e)}")
    
    if download_count > 0:
        st.success(f"✅ Started {download_count} downloads!")
        st.info("💡 Check the 'Download Status' tab to monitor progress.")
    else:
        st.warning("⚠️ No downloads were started.")