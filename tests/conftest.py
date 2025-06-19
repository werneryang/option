import pytest
import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing path to test data directory"""
    return Path(__file__).parent / "data"

@pytest.fixture
def sample_symbols():
    """Fixture providing sample stock symbols for testing"""
    return ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY"]