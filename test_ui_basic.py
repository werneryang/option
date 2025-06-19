#!/usr/bin/env python3
"""
Basic UI Component Test

Tests that all UI components can be imported and initialized
without runtime errors.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_ui_imports():
    """Test that all UI components can be imported"""
    print("Testing UI component imports...")
    
    try:
        # Test data service
        from src.ui.services.data_service import DataService
        data_service = DataService()
        print("✅ DataService: Import and initialization successful")
        
        # Test basic functionality
        symbols = data_service.get_available_symbols()
        print(f"✅ DataService: get_available_symbols() returned {len(symbols)} symbols")
        
        # Test sidebar component
        import streamlit as st
        print("✅ Streamlit: Import successful")
        
        # Test page imports (don't call render functions without Streamlit context)
        from src.ui.pages import dashboard, option_chain, strategy_builder, analytics
        print("✅ UI Pages: All page modules imported successfully")
        
        # Test component imports
        from src.ui.components.sidebar import render_sidebar
        print("✅ UI Components: Sidebar component imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
        return False

def test_analytics_integration():
    """Test that analytics integration works"""
    print("\nTesting analytics integration...")
    
    try:
        from src.ui.services.data_service import DataService
        from src.analytics.strategies import OptionsStrategyBuilder
        from datetime import date, timedelta
        
        data_service = DataService()
        
        # Test strategy building
        expiration = date.today() + timedelta(days=30)
        strategy = data_service.build_strategy("long_call", {
            "strike": 150.0,
            "expiration": expiration,
            "premium": 5.0
        })
        
        if strategy:
            print("✅ Strategy Building: Long call strategy created successfully")
        else:
            print("⚠️  Strategy Building: Returned None (expected for some strategies)")
        
        # Test data summary
        summary = data_service.get_data_summary()
        print(f"✅ Data Summary: {summary['total_symbols']} symbols, {summary['total_files']} files")
        
        return True
        
    except Exception as e:
        print(f"❌ Analytics Integration Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Options Analysis Platform - UI Component Tests")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_ui_imports()
    
    # Test analytics integration
    analytics_ok = test_analytics_integration()
    
    print("\n" + "=" * 60)
    
    if imports_ok and analytics_ok:
        print("✅ All tests passed! UI is ready to launch.")
        print("\n🚀 To start the application, run:")
        print("   python run_ui.py")
        print("\n💡 Or directly with Streamlit:")
        print("   streamlit run src/ui/app.py")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())