#!/usr/bin/env python3
"""
Configure Delayed Market Data for IB TWS
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.data_sources.ib_client import IBClient
from loguru import logger

async def configure_delayed_data():
    """Configure IB TWS to use delayed market data"""
    
    print("🔧 Configuring Delayed Market Data for IB TWS")
    print("=" * 50)
    
    try:
        # Connect to IB TWS
        client = IBClient()
        print("📡 Connecting to IB TWS...")
        
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to IB TWS")
            print("   Make sure TWS is running on port 7497")
            return False
        
        print("✅ Connected to IB TWS successfully")
        
        # Request delayed market data configuration
        print("🔧 Requesting delayed market data...")
        
        # This tells IB to use delayed data when real-time is not available
        client.ib.reqMarketDataType(3)  # 3 = Delayed data
        
        print("✅ Delayed market data type set to 3 (delayed)")
        
        # Test with a simple stock request
        print("🧪 Testing delayed data request...")
        
        try:
            stock_price = await client.get_stock_price("AAPL")
            if stock_price:
                print(f"✅ Test successful - AAPL price: ${stock_price['price']}")
            else:
                print("⚠️  Test returned no data (may be normal)")
        except Exception as e:
            print(f"⚠️  Test failed: {e}")
        
        # Disconnect
        await client.disconnect()
        print("✅ Disconnected from IB TWS")
        
        print()
        print("🎯 NEXT STEPS:")
        print("1. In TWS, go to Account → Management → Market Data Subscription Manager")
        print("2. Enable 'Delayed Market Data' (should be free)")
        print("3. Go to Configure → API → Settings")
        print("4. Check 'Enable delayed data for non-professionals'")
        print("5. Restart TWS")
        print("6. Test snapshot collection again")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(configure_delayed_data())
    if success:
        print("\n✅ Configuration completed successfully!")
    else:
        print("\n❌ Configuration failed - check TWS connection")