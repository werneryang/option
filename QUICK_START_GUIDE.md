# 🚀 Quick Start Guide - Options Analysis Platform

## 📋 Prerequisites

1. **Python 3.9+** installed on your system
2. **Interactive Brokers TWS or IB Gateway** (for live data download)
3. **Web browser** for accessing the interface

## ⚡ 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Initialize Platform
```bash
python main.py setup
```

### Step 3: Download Sample Data (Optional)
```bash
# Start IB TWS first, then:
python main.py download
```

### Step 4: Launch Web Interface
```bash
python run_ui.py
```

### Step 5: Access Application
Open your browser to: **http://localhost:8501**

---

## 🎯 First Time Usage

### 1. **Dashboard Overview**
- View current symbol metrics (AAPL, SPY, TSLA)
- Check data availability status
- Quick navigation to other features

### 2. **Option Chain Analysis**
- Select symbol from sidebar
- Adjust strike range filters
- View Greeks calculations
- Export data as CSV

### 3. **Build Your First Strategy**
- Go to Strategy Builder
- Select "Long Straddle" 
- Adjust strike price and expiration
- View real-time P&L chart

### 4. **Advanced Analytics**
- Explore volatility analysis
- Check historical performance
- Run risk metrics

---

## 🔧 Configuration Options

### Symbol Selection
- Use sidebar to switch between available symbols
- Add new symbols via database (see development guide)

### Risk-Free Rate
- Adjust using sidebar slider
- Affects all Greeks and pricing calculations

### Volatility Parameters
- Customize periods in Analytics page
- Multiple calculation methods available

---

## 📊 Key Features Overview

### **Dashboard Page**
- **Metrics Cards**: Current price, volatility, option count
- **Price Chart**: 30-day price history with interactive Plotly
- **Quick Actions**: Navigate to other features
- **Data Status**: Storage and availability information

### **Option Chain Page**
- **Interactive Table**: Sortable, filterable option data
- **Greeks Display**: Real-time Delta, Gamma, Theta, Vega calculations
- **Strike Filtering**: Adjust range around current price
- **Color Coding**: Visual moneyness indicators (ITM/ATM/OTM)
- **Export**: Download analysis as CSV

### **Strategy Builder Page**
- **Strategy Selection**: 10+ pre-built strategies
- **Parameter Input**: Strike prices, expiration, premiums
- **P&L Visualization**: Interactive profit/loss charts
- **Breakeven Analysis**: Automatic breakeven calculation
- **Risk Metrics**: Max profit, max loss, profit range

### **Analytics Page**
- **Volatility Analysis**: Historical vol across multiple periods
- **Performance Metrics**: Returns, Sharpe ratio, drawdown
- **Risk Analysis**: VaR calculations and distributions
- **Future**: Strategy backtesting (framework ready)

---

## 🎨 Interface Tips

### Navigation
- **Sidebar**: Always available for symbol selection and settings
- **Page Selection**: Radio buttons for main navigation
- **Refresh Data**: Button to clear cache and reload

### Visualizations
- **Interactive Charts**: Hover for details, zoom, pan
- **Responsive Design**: Works on desktop and tablets
- **Export Options**: Download charts and data

### Performance
- **Caching**: First calculations may take longer
- **Progress Indicators**: Shown for long-running operations
- **Error Handling**: Clear messages for issues

---

## 🔍 Troubleshooting

### Common Issues

**"No data available"**
- Run `python main.py download` with IB TWS running
- Check `python main.py status` for data availability

**"Import errors"**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version is 3.9+

**"Greeks calculation failed"**
- Verify option data exists for selected symbol
- Check expiration dates are in the future

**"Streamlit won't start"**
- Port 8501 may be in use
- Try: `streamlit run src/ui/app.py --server.port 8502`

### Getting Help

1. **Check Logs**: `logs/app.log` for detailed error messages
2. **Test Components**: Run `python test_ui_basic.py`
3. **Verify Installation**: Run `python -m pytest tests/`

---

## 📈 Example Workflows

### **Analyze AAPL Options**
1. Select AAPL from sidebar
2. Go to Option Chain page
3. Set strike range 80-120%
4. View Greeks calculations
5. Export interesting strikes

### **Build Iron Condor Strategy**
1. Go to Strategy Builder
2. Select "Iron Condor"
3. Set strikes: 140/145/155/160
4. View P&L diagram
5. Analyze breakeven points

### **Compare Volatility**
1. Go to Analytics page
2. Select "Volatility Analysis"
3. Choose multiple periods (20d, 60d, 252d)
4. View historical trends
5. Analyze current levels vs historical

---

## 🚀 Advanced Usage

### **Adding New Symbols**
```python
from src.data_sources.database import db_manager
db_manager.add_symbol("MSFT", "Microsoft Corp", "Technology")
```

### **Custom Strategies**
- Extend `OptionsStrategyBuilder` class
- Add new strategy methods
- Update UI selection options

### **Enhanced Data Sources**
- Integrate additional data providers
- Add real-time data feeds
- Extend validation rules

---

## 💡 Best Practices

### **Data Management**
- Regular data downloads for current analysis
- Monitor storage usage with `python main.py status`
- Clear cache periodically for fresh calculations

### **Strategy Analysis**
- Always verify input parameters
- Consider multiple scenarios (volatility changes)
- Export important analysis for records

### **Performance**
- Use reasonable strike ranges to avoid slow calculations
- Cache results are automatic but can be cleared
- Monitor system resources for large datasets

---

**🎯 You're now ready to use the Options Analysis Platform for sophisticated options analysis!**

**📊 The platform provides institutional-grade analytics in an accessible web interface.**