#!/usr/bin/env python3
"""
Market Data Scheduler - Run automated hourly collection including 16:00 close
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.scheduler.market_scheduler import MarketScheduler


def main():
    print("🕒 Market Data Scheduler")
    print("=" * 50)
    print("Automated hourly option data collection")
    print("Collection times: 09:30, 10:00, 11:00, 12:00, 13:00, 14:00, 15:00, 16:00")
    print("✅ Includes 16:00 market close snapshot")
    print("📊 Default symbols: AAPL, SPY, TSLA")
    print("=" * 50)
    
    # Allow custom symbols via command line
    if len(sys.argv) > 1:
        symbols = sys.argv[1].split(',')
        print(f"📈 Using custom symbols: {', '.join(symbols)}")
    else:
        symbols = ['AAPL', 'SPY', 'TSLA']
        print(f"📈 Using default symbols: {', '.join(symbols)}")
    
    scheduler = MarketScheduler(symbols)
    
    # Show status
    status = scheduler.get_collection_status()
    print(f"\n📅 Market hours: 09:30 - 16:00 ET")
    print(f"🏪 Currently in market hours: {'Yes' if status['market_hours'] else 'No'}")
    
    print("\n🚀 Starting scheduler...")
    print("Press Ctrl+C to stop\n")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()