"""
Data Management Page

Provides interface for managing dual workflow: real-time snapshots and historical archives.
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

from ...services.async_data_service import async_data_service
from ...services.snapshot_collector import snapshot_collector
from ...services.historical_archiver import historical_archiver
from ...utils.trading_calendar import trading_calendar
from ...utils.async_adapter import run_async_safely, run_async_with_spinner


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


def display_test_results(result: Dict[str, Any]):
    """Display comprehensive test collection results with automatic stopping and detailed reporting"""
    
    # Header with overall status
    if result.get("success"):
        st.success("🎉 **Test Collection Completed Successfully!**")
        st.balloons()  # Celebration for successful test
    else:
        st.error("❌ **Test Collection Failed**")
    
    # Create expandable sections for detailed results
    with st.expander("📊 **Test Summary**", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Status", 
                "✅ SUCCESS" if result.get("success") else "❌ FAILED",
                delta=None
            )
        
        with col2:
            contracts = result.get("contracts", 0)
            st.metric("Contracts Collected", contracts)
        
        with col3:
            total_time = result.get("total_test_time_seconds", 0)
            st.metric("Total Time", f"{total_time:.2f}s")
        
        with col4:
            connection_status = result.get("connection_status", "unknown")
            st.metric("IB Connection", connection_status.upper())
    
    # Performance metrics
    if "performance" in result and result["performance"]:
        with st.expander("⚡ **Performance Metrics**"):
            perf = result["performance"]
            
            perf_col1, perf_col2 = st.columns(2)
            with perf_col1:
                if "connection_time_seconds" in perf:
                    st.metric("Connection Time", f"{perf['connection_time_seconds']:.2f}s")
            
            with perf_col2:
                if "collection_time_seconds" in perf:
                    st.metric("Data Collection Time", f"{perf['collection_time_seconds']:.2f}s")
    
    # Data quality analysis
    if "data_quality" in result and result["data_quality"]:
        with st.expander("🔍 **Data Quality Analysis**"):
            quality = result["data_quality"]
            
            # Quality overview
            qual_col1, qual_col2, qual_col3 = st.columns(3)
            
            with qual_col1:
                st.metric("Call Contracts", quality.get("call_contracts", 0))
                st.metric("Put Contracts", quality.get("put_contracts", 0))
            
            with qual_col2:
                st.metric("Unique Expirations", quality.get("unique_expirations", 0))
                st.metric("Unique Strikes", quality.get("unique_strikes", 0))
            
            with qual_col3:
                completeness = quality.get("price_data_completeness", 0)
                st.metric("Price Data Completeness", f"{completeness:.1f}%")
                
                # Color code completeness
                if completeness >= 80:
                    st.success("Excellent data quality")
                elif completeness >= 60:
                    st.warning("Good data quality")
                else:
                    st.error("Poor data quality")
            
            # Quality issues
            if quality.get("issues"):
                st.markdown("**⚠️ Data Quality Issues:**")
                for issue in quality["issues"]:
                    st.warning(f"• {issue}")
    
    # Errors and warnings
    if result.get("errors") or result.get("warnings"):
        with st.expander("⚠️ **Issues and Warnings**"):
            if result.get("errors"):
                st.markdown("**🔴 Errors:**")
                for error in result["errors"]:
                    st.error(f"• {error}")
            
            if result.get("warnings"):
                st.markdown("**🟡 Warnings:**")
                for warning in result["warnings"]:
                    st.warning(f"• {warning}")
    
    # Technical details
    with st.expander("🔧 **Technical Details**"):
        tech_col1, tech_col2 = st.columns(2)
        
        with tech_col1:
            st.write("**Test Parameters:**")
            st.write(f"• Symbol: {result.get('symbol', 'Unknown')}")
            st.write(f"• Start Time: {result.get('test_start_time', 'Unknown')}")
            st.write(f"• End Time: {result.get('test_end_time', 'Unknown')}")
        
        with tech_col2:
            st.write("**Collection Details:**")
            st.write(f"• Timestamp: {result.get('timestamp', 'None')}")
            st.write(f"• Connection Status: {result.get('connection_status', 'Unknown')}")
            
            if result.get("data_quality"):
                vol_count = result["data_quality"].get("has_volume", 0)
                st.write(f"• Contracts with Volume: {vol_count}")
    
    # Automatic result summary
    st.markdown("---")
    if result.get("success"):
        st.success(
            f"✅ **Test completed automatically!** "
            f"Successfully collected {result.get('contracts', 0)} option contracts "
            f"for {result.get('symbol', 'unknown symbol')} "
            f"in {result.get('total_test_time_seconds', 0):.2f} seconds."
        )
        
        # Provide next steps
        st.info(
            "💡 **Next Steps:**\n"
            "• The test has automatically stopped and saved results\n"
            "• Data is now available in the option chain viewer\n"
            "• Check the 'Data Status' tab for more details\n"
            "• Consider starting the full snapshot collection service if test was successful"
        )
    else:
        st.error(
            f"❌ **Test failed automatically.** "
            f"Error: {result.get('error', 'Unknown error')}. "
            f"Test duration: {result.get('total_test_time_seconds', 0):.2f} seconds."
        )
        
        # Provide troubleshooting tips
        st.info(
            "🔧 **Troubleshooting Tips:**\n"
            "• Ensure IB TWS is running and connected\n"
            "• Check that API connections are enabled in TWS\n"
            "• Verify delayed market data is configured\n"
            "• Try during market hours for live data"
        )


def render():
    """Render the data management page with dual workflow support"""
    
    st.header("📊 Data Management")
    st.markdown("Manage real-time snapshots and historical archives for comprehensive options analysis.")
    
    # Initialize and clean up session state
    cleanup_old_downloads()
    
    # Create tabs for different functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📸 Snapshot Collection", 
        "📚 Historical Archive", 
        "🔍 Data Status", 
        "📈 Download Status", 
        "⚙️ System Operations"
    ])
    
    with tab1:
        render_snapshot_management()
    
    with tab2:
        render_historical_archiver()
    
    with tab3:
        render_data_status()
    
    with tab4:
        render_download_status()
    
    with tab5:
        render_system_operations()


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
    
    # Display connection warning
    st.warning("⚠️ **Important**: This requires IB TWS (Interactive Brokers Trader Workstation) to be running and connected. If TWS is not running, the download will fail with 'Not connected to IB TWS' error.")
    
    # Start the background download
    task_id = async_data_service.start_background_download(symbol, download_types)
    
    # Store task ID with timestamp to avoid conflicts
    st.session_state.active_downloads[f"{symbol}_{task_id}"] = task_id
    
    action_type = "Force download" if force else "Download"
    st.success(f"✅ {action_type} started for {symbol}!")
    st.info(f"📋 Task ID: {task_id}")
    st.info("💡 Check the 'Download Status' tab to monitor progress.")
    st.info("🔌 If download fails, ensure IB TWS is running and connected.")


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
        
        st.dataframe(downloads_df, use_container_width=True)
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
                st.dataframe(df, use_container_width=True)
                
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
            st.dataframe(df, use_container_width=True)
            
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


# === NEW UI COMPONENTS FOR DUAL WORKFLOW ===

def render_snapshot_management():
    """Render snapshot collection management interface"""
    st.markdown("### 📸 Real-time Snapshot Collection")
    st.markdown("Automated collection of delayed option chain snapshots every 5 minutes during market hours.")
    
    # Get snapshot collector status
    status = snapshot_collector.get_status()
    
    # Status display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if status["is_running"]:
            st.success("🟢 Collection Active")
        else:
            st.error("🔴 Collection Stopped")
    
    with col2:
        if status["is_market_hours"]:
            st.info("🕐 Market Hours")
        else:
            st.warning("🕐 After Hours")
    
    with col3:
        if status["is_trading_day"]:
            st.info("📅 Trading Day")
        else:
            st.warning("📅 Holiday/Weekend")
    
    # Configuration display
    st.markdown("#### ⚙️ Collection Settings")
    
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        st.metric("Collection Interval", f"{status['collection_interval']}")
        st.metric("Market Hours", status["market_hours"])
    
    with config_col2:
        st.metric("Next Collection", "Available" if status["should_collect_now"] else "Waiting")
        st.metric("IB Connection", "Connected" if status["ib_connected"] else "Disconnected")
    
    # Controls
    st.markdown("#### 🎛️ Collection Controls")
    
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
    
    with ctrl_col1:
        if st.button("▶️ Start Collection", disabled=status["is_running"]):
            if snapshot_collector.start_collection():
                st.success("✅ Snapshot collection started!")
                st.rerun()
            else:
                st.error("❌ Failed to start collection")
    
    with ctrl_col2:
        if st.button("⏹️ Stop Collection", disabled=not status["is_running"]):
            if snapshot_collector.stop_collection():
                st.success("✅ Snapshot collection stopped!")
                st.rerun()
            else:
                st.error("❌ Failed to stop collection")
    
    with ctrl_col3:
        test_symbol = st.selectbox("Test Symbol", get_available_symbols(), key="test_snapshot_symbol")
        if st.button("🧪 Test Collection"):
            try:
                # Show initial status
                status_placeholder = st.empty()
                status_placeholder.info("🔄 Starting test collection...")
                
                # Run test with shorter timeout for UI responsiveness
                result = run_async_with_spinner(
                    snapshot_collector.collect_now(test_symbol),
                    f"Testing snapshot collection for {test_symbol} (max 60s)..."
                )
                
                # Clear status and show results
                status_placeholder.empty()
                
                # Display comprehensive test results
                display_test_results(result)
                
            except Exception as e:
                st.error(f"❌ Test error: {str(e)}")
                
                # Show basic troubleshooting if test fails
                with st.expander("🔧 Troubleshooting"):
                    st.markdown("""
                    **Common Issues:**
                    - IB TWS not running or not connected
                    - API connections disabled in TWS settings
                    - Market data subscriptions not configured
                    - Network connectivity issues
                    
                    **Quick Checks:**
                    1. Ensure TWS is running on port 7497
                    2. Enable API connections in TWS settings
                    3. Configure delayed market data
                    4. Try during market hours for better data
                    """)
    
    # Recent snapshots summary
    st.markdown("#### 📊 Recent Snapshot Activity")
    
    data_service = st.session_state.get('data_service')
    if data_service:
        try:
            available_symbols = get_available_symbols()[:5]  # Show first 5 symbols
            snapshot_summaries = []
            
            for symbol in available_symbols:
                summary = data_service.get_snapshot_summary(symbol)
                snapshot_summaries.append({
                    "Symbol": symbol,
                    "Date": summary.get("date", "N/A"),
                    "Snapshots": summary.get("snapshot_count", 0),
                    "Contracts": summary.get("unique_contracts", 0),
                    "Latest": summary.get("latest_snapshot", "N/A"),
                    "Volume": summary.get("total_volume", 0)
                })
            
            if snapshot_summaries:
                df = pd.DataFrame(snapshot_summaries)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No snapshot data available yet")
                
        except Exception as e:
            st.error(f"Error loading snapshot summary: {str(e)}")


def render_historical_archiver():
    """Render historical data archiver interface"""
    st.markdown("### 📚 Historical Data Archive")
    st.markdown("Download and consolidate historical option data for long-term analysis.")
    
    # Archive status overview
    try:
        all_status = historical_archiver.get_all_archive_status()
        
        if all_status:
            st.markdown("#### 📊 Archive Status Overview")
            
            status_data = []
            for symbol, status in all_status.items():
                status_data.append({
                    "Symbol": symbol,
                    "Has Archive": "✅" if status.get("has_archive", False) else "❌",
                    "Last Archive": status.get("last_archive_date", "Never"),
                    "Records": status.get("archive_records", 0),
                    "Days Behind": status.get("days_behind", 0),
                    "Needs Update": "🔄" if status.get("needs_update", False) else "✅"
                })
            
            df = pd.DataFrame(status_data)
            st.dataframe(df, use_container_width=True)
            
            # Summary metrics
            total_symbols = len(status_data)
            needs_update = len([s for s in status_data if s["Needs Update"] == "🔄"])
            has_archive = len([s for s in status_data if s["Has Archive"] == "✅"])
            
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("Total Symbols", total_symbols)
            with metric_col2:
                st.metric("Has Archive", has_archive)
            with metric_col3:
                st.metric("Needs Update", needs_update)
        
    except Exception as e:
        st.error(f"Error loading archive status: {str(e)}")
    
    # Archive operations
    st.markdown("#### 🔄 Archive Operations")
    
    # Single symbol archive
    st.markdown("##### Single Symbol Archive")
    
    archive_col1, archive_col2, archive_col3 = st.columns(3)
    
    with archive_col1:
        selected_symbol = st.selectbox("Select Symbol", get_available_symbols(), key="archive_symbol")
    
    with archive_col2:
        # Show status for selected symbol
        if selected_symbol:
            try:
                symbol_status = historical_archiver.get_archive_status(selected_symbol)
                if symbol_status.get("needs_update", False):
                    st.warning(f"📅 {symbol_status.get('days_behind', 0)} days behind")
                else:
                    st.success("✅ Up to date")
            except:
                st.info("Status unknown")
    
    with archive_col3:
        if st.button("📥 Archive Symbol", key="archive_single"):
            if selected_symbol:
                try:
                    result = run_async_with_spinner(
                        historical_archiver.archive_symbol(selected_symbol),
                        f"Archiving historical data for {selected_symbol}..."
                    )
                    if result["success"]:
                        st.success(f"✅ Archive successful: {result['records_downloaded']} new records")
                    else:
                        st.error(f"❌ Archive failed: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Archive error: {str(e)}")
    
    # Bulk archive operations
    st.markdown("##### Bulk Archive Operations")
    
    bulk_col1, bulk_col2 = st.columns(2)
    
    with bulk_col1:
        bulk_symbols = st.multiselect(
            "Select Symbols for Bulk Archive",
            get_available_symbols(),
            key="bulk_archive_symbols"
        )
        # Debug info to show what's actually selected
        if bulk_symbols:
            st.info(f"✅ Selected: {len(bulk_symbols)} symbols - {', '.join(bulk_symbols)}")
        else:
            st.info("ℹ️ No symbols selected yet")
    
    with bulk_col2:
        st.markdown("")  # Spacing
        
        # Clear selection button
        if st.button("🗑️ Clear Selection", key="clear_bulk_selection"):
            st.session_state.bulk_archive_symbols = []
            st.rerun()
        
        if st.button("📥 Archive Selected", disabled=not bulk_symbols):
            try:
                result = run_async_with_spinner(
                    historical_archiver.archive_multiple_symbols(bulk_symbols),
                    f"Archiving {len(bulk_symbols)} symbols..."
                )
                
                # Show results
                st.success(f"✅ Bulk archive completed: {result['symbols_successful']}/{result['symbols_processed']} successful")
                st.info(f"📊 Total records downloaded: {result['total_records_downloaded']}")
                
                if result['errors']:
                    st.error("❌ Some errors occurred:")
                    for error in result['errors']:
                        st.error(f"  • {error}")
                
            except Exception as e:
                st.error(f"❌ Bulk archive error: {str(e)}")


def render_data_status():
    """Render comprehensive data status overview"""
    st.markdown("### 🔍 Data Status Overview")
    st.markdown("View status of all data types: snapshots, archives, and legacy processed data.")
    
    data_service = st.session_state.get('data_service')
    if not data_service:
        st.error("Data service not available")
        return
    
    # Get comprehensive data summary
    try:
        # Legacy data summary
        legacy_summary = data_service.get_data_summary()
        
        st.markdown("#### 📊 Data Summary")
        
        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
        
        with summary_col1:
            st.metric("Total Symbols", legacy_summary.get("total_symbols", 0))
        
        with summary_col2:
            st.metric("Total Files", legacy_summary.get("total_files", 0))
        
        with summary_col3:
            st.metric("Storage (MB)", f"{legacy_summary.get('total_size_mb', 0):.1f}")
        
        with summary_col4:
            st.metric("Recent Downloads", legacy_summary.get("recent_downloads", 0))
        
        # Detailed symbol data
        symbols = get_available_symbols()
        
        st.markdown("#### 📋 Symbol Data Status")
        
        status_data = []
        for symbol in symbols:
            try:
                # Snapshot data
                snapshot_summary = data_service.get_snapshot_summary(symbol)
                
                # Archive data
                archive_summary = data_service.get_archive_summary(symbol)
                
                # Legacy data (option chain)
                legacy_dates = data_service.get_available_option_dates(symbol)
                
                status_data.append({
                    "Symbol": symbol,
                    "Snapshots": snapshot_summary.get("snapshot_count", 0),
                    "Snapshot Date": snapshot_summary.get("date", "N/A"),
                    "Archive Records": archive_summary.get("archive_records", 0),
                    "Archive Range": f"{archive_summary.get('date_range', [None, None])[0]} to {archive_summary.get('date_range', [None, None])[1]}" if archive_summary.get('date_range') else "N/A",
                    "Legacy Dates": len(legacy_dates),
                    "Latest Legacy": max(legacy_dates) if legacy_dates else "N/A"
                })
            except Exception as e:
                status_data.append({
                    "Symbol": symbol,
                    "Snapshots": "Error",
                    "Snapshot Date": "Error",
                    "Archive Records": "Error", 
                    "Archive Range": "Error",
                    "Legacy Dates": "Error",
                    "Latest Legacy": "Error"
                })
        
        if status_data:
            df = pd.DataFrame(status_data)
            st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading data status: {str(e)}")


def render_system_operations():
    """Render system maintenance and operations"""
    st.markdown("### ⚙️ System Operations")
    st.markdown("System maintenance, cleanup, and configuration operations.")
    
    # Data cleanup operations
    st.markdown("#### 🧹 Data Cleanup")
    
    cleanup_col1, cleanup_col2 = st.columns(2)
    
    with cleanup_col1:
        retention_days = st.number_input(
            "Snapshot Retention (days)",
            min_value=1,
            max_value=365,
            value=90,
            help="Number of days to keep snapshot data"
        )
    
    with cleanup_col2:
        st.markdown("")  # Spacing
        st.markdown("")  # Spacing
        if st.button("🧹 Cleanup Old Snapshots"):
            with st.spinner("Cleaning up old snapshot data..."):
                try:
                    data_service = st.session_state.get('data_service')
                    if data_service:
                        result = data_service.cleanup_old_data(retention_days)
                        st.success(f"✅ Cleanup completed: {result['files_deleted']} files deleted from {result['symbols_processed']} symbols")
                    else:
                        st.error("Data service not available")
                except Exception as e:
                    st.error(f"❌ Cleanup error: {str(e)}")
    
    # Cache operations
    st.markdown("#### 💾 Cache Management")
    
    cache_col1, cache_col2 = st.columns(2)
    
    with cache_col1:
        st.info("Clear analytics cache to free memory and force recalculation of Greeks and other computed values.")
    
    with cache_col2:
        if st.button("🗑️ Clear Cache"):
            try:
                data_service = st.session_state.get('data_service')
                if data_service:
                    data_service.clear_cache()
                    st.success("✅ Cache cleared successfully")
                else:
                    st.error("Data service not available")
            except Exception as e:
                st.error(f"❌ Cache clear error: {str(e)}")
    
    # System status
    st.markdown("#### 📊 System Status")
    
    try:
        import psutil
        
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            memory = psutil.virtual_memory()
            st.metric("Memory Usage", f"{memory.percent:.1f}%")
        
        with status_col2:
            disk = psutil.disk_usage('/')
            st.metric("Disk Usage", f"{disk.percent:.1f}%")
        
        with status_col3:
            cpu = psutil.cpu_percent(interval=1)
            st.metric("CPU Usage", f"{cpu:.1f}%")
    
    except ImportError:
        st.info("Install psutil for system monitoring: pip install psutil")