#!/usr/bin/env python3
"""
Download Apple Historical Options Data - Past Month
专门下载Apple过去一个月的历史期权数据
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.data_sources.ib_client import IBClient

async def download_apple_monthly():
    print("📈 Downloading Apple Historical Options Data - Past Month")
    print("=" * 60)
    
    client = IBClient()
    
    try:
        # Connect to TWS
        print("🔗 Connecting to TWS...")
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to TWS")
            return False
        
        print("✅ Connected successfully!")
        print("📊 Starting Apple (AAPL) historical options download...")
        print("📅 Time Range: Past 1 month (ending yesterday)")
        print("📋 Data Level: Daily bars")
        print("⏰ Expected Duration: 2-5 minutes\n")
        
        # Download 1 month of Apple options data
        start_time = datetime.now()
        option_data = await client.get_historical_option_data("AAPL", duration="1 M")
        end_time = datetime.now()
        
        if option_data is not None and len(option_data) > 0:
            print(f"\n✅ Download completed successfully!")
            print(f"⏱️  Duration: {(end_time - start_time).total_seconds():.1f} seconds")
            print(f"📊 Total records: {len(option_data)}")
            print(f"📅 Date range: {option_data['date'].min()} to {option_data['date'].max()}")
            print(f"🗓️  Trading days: {len(option_data.groupby('date'))}")
            
            # Show breakdown by option type
            type_counts = option_data['option_type'].value_counts()
            print(f"📈 Call options: {type_counts.get('C', 0)}")
            print(f"📉 Put options: {type_counts.get('P', 0)}")
            
            # Show strike range
            strikes = option_data['strike'].unique()
            print(f"🎯 Strike range: ${min(strikes):.1f} - ${max(strikes):.1f}")
            print(f"🔢 Total strikes: {len(strikes)}")
            
            # Show sample data
            print(f"\n📋 Sample data preview:")
            sample = option_data[['date', 'strike', 'option_type', 'open', 'high', 'low', 'close', 'volume']].head(5)
            print(sample.to_string(index=False))
            
            # Show data by date
            print(f"\n📊 Records by date:")
            date_counts = option_data.groupby('date').size().sort_index()
            for date_val, count in date_counts.tail(10).items():  # Show last 10 dates
                print(f"   {date_val}: {count} records")
            
            return True
            
        else:
            print("❌ No historical option data retrieved")
            return False
            
    except Exception as e:
        print(f"❌ Error during download: {e}")
        return False
    finally:
        await client.disconnect()
        print("\n🔌 Disconnected from TWS")

def main():
    print("🍎 Apple Historical Options Data Downloader")
    print("📡 Connecting to Interactive Brokers TWS...\n")
    
    try:
        success = asyncio.run(download_apple_monthly())
        
        if success:
            print("\n🎉 Download completed successfully!")
            print("\n🚀 Next steps:")
            print("   1. Run UI: python start_ui.py")
            print("   2. Go to Option Chain page")
            print("   3. Enable Historical Analysis Mode")
            print("   4. Select different dates to explore the data")
            print("   5. Use date range for trend analysis")
            
            print("\n💡 You now have:")
            print("   • Up to 1 month of Apple options history")
            print("   • Daily OHLC data for each option")
            print("   • Multiple strikes and expirations")
            print("   • Volume and pricing information")
            
        else:
            print("\n❌ Download failed.")
            print("💡 Troubleshooting:")
            print("   • Ensure TWS is running and API is enabled")
            print("   • Check if using paper trading account")
            print("   • Verify historical data permissions")
            
    except KeyboardInterrupt:
        print("\n🛑 Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()