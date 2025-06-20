#!/usr/bin/env python3
"""
Historical Options Data Demo
Demonstrates enhanced historical data retrieval and analysis capabilities
"""

import sys
import pandas as pd
from datetime import date, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.ui.services.data_service import DataService
from src.data_sources.storage import ParquetStorage
from src.data_sources.ib_client import IBClient
from src.data_sources.database import DatabaseManager

def main():
    print("🔍 Historical Options Data Analysis Demo")
    print("=" * 50)
    
    # Initialize services
    data_service = DataService()
    storage = ParquetStorage()
    
    # Get available symbols
    symbols = data_service.get_available_symbols()
    print(f"\n📊 Available symbols: {symbols}")
    
    if not symbols:
        print("❌ No symbols found. You may need to download data first.")
        print("Run: python main.py download")
        return
    
    # Check current data status
    print("\n📈 Current Data Summary:")
    summary = data_service.get_data_summary()
    print(f"   • Total symbols: {summary['total_symbols']}")
    print(f"   • Total files: {summary['total_files']}")
    print(f"   • Total size: {summary['total_size_mb']} MB")
    print(f"   • Recent downloads: {summary['recent_downloads']}")
    
    # Check historical coverage
    if 'historical_coverage' in summary:
        print("\n📅 Historical Coverage:")
        for symbol, coverage in summary['historical_coverage'].items():
            print(f"   {symbol}:")
            print(f"     • Option dates: {coverage['option_dates']}")
            print(f"     • Date range: {coverage['date_range']}")
            print(f"     • Total records: {coverage['total_option_records']}")
            print(f"     • Latest: {coverage['latest_option_date']}")
    
    # Demo with first available symbol
    if symbols:
        symbol = symbols[0]
        print(f"\n🎯 Analyzing {symbol}")
        
        # Check available option dates
        option_dates = data_service.get_available_option_dates(symbol)
        print(f"   • Available option dates: {len(option_dates)}")
        if option_dates:
            print(f"   • Date range: {min(option_dates)} to {max(option_dates)}")
        
        # Get current price
        current_price = data_service.get_current_price(symbol)
        print(f"   • Current price: ${current_price:.2f}" if current_price else "   • Current price: Not available")
        
        # Get recent price history
        price_history = data_service.get_price_history(symbol, days=30)
        if price_history is not None:
            print(f"   • Price history records: {len(price_history)}")
            recent_prices = price_history.tail(5)[['date', 'close']]
            print("   • Recent prices:")
            for _, row in recent_prices.iterrows():
                print(f"     {row['date']}: ${row['close']:.2f}")
        
        # Try to get historical option chains if available
        if option_dates:
            print(f"\n⛓️  Latest Option Chain Analysis:")
            latest_date = max(option_dates)
            option_chain = data_service.get_option_chain(symbol, latest_date)
            
            if option_chain is not None:
                print(f"   • Chain date: {latest_date}")
                print(f"   • Total options: {len(option_chain)}")
                
                # Show option types breakdown
                if 'option_type' in option_chain.columns:
                    type_counts = option_chain['option_type'].value_counts()
                    print(f"   • Calls: {type_counts.get('C', 0)}, Puts: {type_counts.get('P', 0)}")
                
                # Show strike range
                if 'strike' in option_chain.columns:
                    strikes = option_chain['strike']
                    print(f"   • Strike range: ${strikes.min():.2f} - ${strikes.max():.2f}")
                
                # Show sample options
                print("   • Sample options:")
                sample_options = option_chain[['strike', 'option_type', 'bid', 'ask']].head(3)
                for _, row in sample_options.iterrows():
                    print(f"     ${row['strike']:.0f} {row['option_type']}: ${row['bid']:.2f}/${row['ask']:.2f}")
        
        # Demo volatility analysis
        print(f"\n📊 Volatility Analysis (30d):")
        vol_analysis = data_service.get_volatility_analysis(symbol, [30])
        if vol_analysis:
            for period, vol in vol_analysis.items():
                print(f"   • {period}: {vol:.2%}" if vol else f"   • {period}: Not available")
        else:
            print("   • Volatility data not available")
    
    print(f"\n✅ Demo completed! Historical data functionality is enhanced.")
    print("\n💡 Next steps:")
    print("   1. Download historical option chains: python main.py download")
    print("   2. Run full UI: python run_ui.py")
    print("   3. Try simple UI: python ultra_simple_ui.py")

if __name__ == "__main__":
    main()