#!/usr/bin/env python3
"""
Flask API Backend for Options Analysis Platform - Local Desktop Application

Provides RESTful APIs for historical options data analysis and education.
Local-only platform focused on research and learning, NOT real-time trading.
"""

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import pandas as pd
import json

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.ui.services.data_service import DataService
from src.data_sources.storage import ParquetStorage

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize services
data_service = DataService()
storage = ParquetStorage()

# Simple HTML template with Vue.js
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Options Analysis Platform - Local Desktop</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: 500; }
        .btn-primary { background: #667eea; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn:hover { opacity: 0.9; }
        .form-group { margin-bottom: 15px; }
        .form-control { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .table th, .table td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        .table th { background: #f8f9fa; font-weight: 600; }
        .metric { text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .metric-label { color: #666; margin-top: 5px; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .error { color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .success { color: #155724; background: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0; }
        .historical-toggle { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .date-selector { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
    </style>
</head>
<body>
    {% raw %}
    <div id="app">
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>📈 Options Analysis Platform</h1>
                <p>Local Desktop • Historical Data Analysis • Educational Platform • No Real-time Trading</p>
            </div>

            <!-- Navigation -->
            <div class="card">
                <div class="controls">
                    <button class="btn btn-primary" @click="currentPage = 'dashboard'" :class="{active: currentPage === 'dashboard'}">
                        📊 Dashboard
                    </button>
                    <button class="btn btn-primary" @click="currentPage = 'options'" :class="{active: currentPage === 'options'}">
                        🔗 Option Chain
                    </button>
                    <button class="btn btn-primary" @click="currentPage = 'analytics'" :class="{active: currentPage === 'analytics'}">
                        📈 Analytics
                    </button>
                </div>
            </div>

            <!-- Dashboard Page -->
            <div v-if="currentPage === 'dashboard'">
                <div class="card">
                    <h2>📋 Data Overview</h2>
                    <div class="grid">
                        <div class="metric">
                            <div class="metric-value">{{ summary.total_symbols ? summary.total_symbols : 0 }}</div>
                            <div class="metric-label">Symbols</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{{ Object.keys(summary.historical_coverage ? summary.historical_coverage : {}).length }}</div>
                            <div class="metric-label">With Historical Data</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{{ summary.total_files ? summary.total_files : 0 }}</div>
                            <div class="metric-label">Data Files</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{{ (summary.total_size_mb ? summary.total_size_mb : 0).toFixed(2) }} MB</div>
                            <div class="metric-label">Total Size</div>
                        </div>
                    </div>
                </div>

                <div class="card" v-if="summary.historical_coverage">
                    <h3>📅 Historical Coverage</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Option Dates</th>
                                <th>Total Records</th>
                                <th>Date Range</th>
                                <th>Latest Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(coverage, symbol) in summary.historical_coverage" :key="symbol">
                                <td><strong>{{ symbol }}</strong></td>
                                <td>{{ coverage.option_dates }}</td>
                                <td>{{ coverage.total_option_records }}</td>
                                <td>{{ formatDateRange(coverage.date_range) }}</td>
                                <td>{{ coverage.latest_option_date }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Options Page -->
            <div v-if="currentPage === 'options'">
                <div class="card">
                    <h2>🔗 Option Chain Analysis</h2>
                    
                    <!-- Symbol Selection -->
                    <div class="form-group">
                        <label>Select Symbol:</label>
                        <select class="form-control" v-model="selectedSymbol" @change="loadSymbolData" style="width: 200px;">
                            <option v-for="symbol in symbols" :key="symbol" :value="symbol">{{ symbol }}</option>
                        </select>
                    </div>

                    <!-- Current Price -->
                    <div v-if="currentPrice" class="success">
                        Current Price: ${{ currentPrice.toFixed(2) }}
                    </div>

                    <!-- Historical Mode Toggle -->
                    <div class="historical-toggle">
                        <label>
                            <input type="checkbox" v-model="historicalMode" @change="onHistoricalModeChange"> 
                            📊 Historical Analysis Mode
                        </label>
                        <p v-if="historicalMode" style="margin: 10px 0 0 0; color: #666;">
                            Available dates: {{ availableDates.length }} | Range: {{ dateRangeText }}
                        </p>
                        
                        <div v-if="historicalMode && availableDates.length > 0" class="date-selector">
                            <div>
                                <label>Target Date:</label>
                                <select class="form-control" v-model="selectedDate" @change="loadOptionChain">
                                    <option v-for="date in availableDates" :key="date" :value="date">{{ date }}</option>
                                </select>
                            </div>
                            <div>
                                <label>Date Range (for trends):</label>
                                <select class="form-control" v-model="startDate">
                                    <option v-for="date in availableDates" :key="date" :value="date">{{ date }} (Start)</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Option Chain Data -->
                    <div v-if="loading" class="loading">Loading option chain data...</div>
                    <div v-else-if="optionChain.length > 0">
                        <h3>📊 Option Chain Data</h3>
                        <p><strong>{{ optionChain.length }}</strong> options found</p>
                        
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Strike</th>
                                    <th>Type</th>
                                    <th>Open</th>
                                    <th>High</th>
                                    <th>Low</th>
                                    <th>Close</th>
                                    <th>Volume</th>
                                    <th v-if="historicalMode">Date/Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="option in optionChain.slice(0, 50)" :key="option.id">
                                    <td>${{ option.strike }}</td>
                                    <td>{{ option.option_type }}</td>
                                    <td>${{ option.open.toFixed(2) }}</td>
                                    <td>${{ option.high.toFixed(2) }}</td>
                                    <td>${{ option.low.toFixed(2) }}</td>
                                    <td>${{ option.close.toFixed(2) }}</td>
                                    <td>{{ option.volume }}</td>
                                    <td v-if="historicalMode">{{ option.datetime ? option.datetime : option.date }}</td>
                                </tr>
                            </tbody>
                        </table>
                        <p v-if="optionChain.length > 50" style="color: #666;">Showing first 50 of {{ optionChain.length }} records</p>
                    </div>
                    <div v-else-if="!loading && selectedSymbol">
                        <div class="error">No option chain data found for {{ selectedSymbol }}</div>
                    </div>
                </div>
            </div>

            <!-- Analytics Page -->
            <div v-if="currentPage === 'analytics'">
                <div class="card">
                    <h2>📈 Advanced Analytics</h2>
                    <p>Coming soon: Historical volatility analysis, Greeks evolution, strategy backtesting</p>
                </div>
            </div>

            <!-- Footer -->
            <div class="card" style="text-align: center; color: #666;">
                Options Analysis Platform | Flask + Vue.js | Historical Data Analysis
            </div>
        </div>
    </div>
    {% endraw %}

    <script>
        const { createApp } = Vue;

        createApp({
            data() {
                return {
                    currentPage: 'dashboard',
                    summary: {},
                    symbols: [],
                    selectedSymbol: '',
                    currentPrice: null,
                    historicalMode: false,
                    availableDates: [],
                    selectedDate: '',
                    startDate: '',
                    optionChain: [],
                    loading: false
                }
            },
            computed: {
                dateRangeText() {
                    if (this.availableDates.length === 0) return 'No data';
                    const sorted = [...this.availableDates].sort();
                    return `${sorted[0]} to ${sorted[sorted.length - 1]}`;
                }
            },
            methods: {
                async loadData() {
                    try {
                        // Load summary
                        const summaryResponse = await axios.get('/api/summary');
                        this.summary = summaryResponse.data;

                        // Load symbols
                        const symbolsResponse = await axios.get('/api/symbols');
                        this.symbols = symbolsResponse.data;
                        
                        if (this.symbols.length > 0 && !this.selectedSymbol) {
                            this.selectedSymbol = this.symbols[0];
                            await this.loadSymbolData();
                        }
                    } catch (error) {
                        console.error('Error loading data:', error);
                    }
                },
                async loadSymbolData() {
                    if (!this.selectedSymbol) return;
                    
                    try {
                        // Load current price
                        const priceResponse = await axios.get(`/api/price/${this.selectedSymbol}`);
                        this.currentPrice = priceResponse.data.price;

                        // Load available dates
                        const datesResponse = await axios.get(`/api/dates/${this.selectedSymbol}`);
                        this.availableDates = datesResponse.data.dates.sort().reverse();
                        
                        if (this.availableDates.length > 0) {
                            this.selectedDate = this.availableDates[0];
                            this.startDate = this.availableDates[Math.max(0, this.availableDates.length - 7)];
                        }

                        await this.loadOptionChain();
                    } catch (error) {
                        console.error('Error loading symbol data:', error);
                    }
                },
                async loadOptionChain() {
                    if (!this.selectedSymbol) return;
                    
                    this.loading = true;
                    try {
                        let url = `/api/options/${this.selectedSymbol}`;
                        if (this.historicalMode && this.selectedDate) {
                            url += `?date=${this.selectedDate}`;
                        }
                        
                        const response = await axios.get(url);
                        this.optionChain = response.data.options ? response.data.options : [];
                    } catch (error) {
                        console.error('Error loading option chain:', error);
                        this.optionChain = [];
                    } finally {
                        this.loading = false;
                    }
                },
                async onHistoricalModeChange() {
                    await this.loadOptionChain();
                },
                formatDateRange(range) {
                    if (!range || !Array.isArray(range)) return 'N/A';
                    return `${range[0]} to ${range[1]}`;
                }
            },
            async mounted() {
                await this.loadData();
            }
        }).mount('#app');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main Vue.js application"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/summary')
def api_summary():
    """Get data summary"""
    try:
        summary = data_service.get_data_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/symbols')
def api_symbols():
    """Get available symbols"""
    try:
        symbols = data_service.get_available_symbols()
        return jsonify(symbols)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/price/<symbol>')
def api_price(symbol):
    """Get current price for symbol"""
    try:
        price = data_service.get_current_price(symbol)
        return jsonify({'symbol': symbol, 'price': price})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dates/<symbol>')
def api_dates(symbol):
    """Get available dates for symbol"""
    try:
        dates = data_service.get_available_option_dates(symbol)
        # Convert date objects to strings
        date_strings = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in dates]
        return jsonify({'symbol': symbol, 'dates': date_strings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/options/<symbol>')
def api_options(symbol):
    """Get option chain for symbol"""
    try:
        target_date = request.args.get('date')
        
        if target_date:
            # Historical data
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
            option_chain = data_service.get_option_chain(symbol, target_date_obj)
        else:
            # Latest data
            option_chain = data_service.get_option_chain(symbol)
        
        if option_chain is not None:
            # Convert DataFrame to list of dictionaries
            options_list = []
            for idx, row in option_chain.iterrows():
                option_dict = row.to_dict()
                # Convert date objects to strings
                for key, value in option_dict.items():
                    if hasattr(value, 'strftime'):
                        option_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S') if hasattr(value, 'hour') else value.strftime('%Y-%m-%d')
                    elif pd.isna(value):
                        option_dict[key] = 0
                option_dict['id'] = idx
                options_list.append(option_dict)
            
            return jsonify({
                'symbol': symbol,
                'date': target_date,
                'count': len(options_list),
                'options': options_list
            })
        else:
            return jsonify({'symbol': symbol, 'options': []})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical/<symbol>')
def api_historical(symbol):
    """Get historical option data for date range"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date and end_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            historical_data = data_service.get_historical_option_chains(symbol, start_date_obj, end_date_obj)
            
            if historical_data is not None:
                # Convert to JSON-serializable format
                data_list = []
                for idx, row in historical_data.iterrows():
                    data_dict = row.to_dict()
                    for key, value in data_dict.items():
                        if hasattr(value, 'strftime'):
                            data_dict[key] = value.strftime('%Y-%m-%d')
                        elif pd.isna(value):
                            data_dict[key] = 0
                    data_list.append(data_dict)
                
                return jsonify({
                    'symbol': symbol,
                    'start_date': start_date,
                    'end_date': end_date,
                    'count': len(data_list),
                    'data': data_list
                })
            else:
                return jsonify({'symbol': symbol, 'data': []})
        else:
            return jsonify({'error': 'start_date and end_date required'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Flask API is running",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Options Analysis Platform - Flask + Vue.js")
    print("📊 Backend: Flask REST API")
    print("🎨 Frontend: Vue.js SPA")
    print("📡 Data: Historical Options Analysis")
    print("\n🌐 Access the application at: http://localhost:8080")
    print("📋 API health check at: http://localhost:8080/health\n")
    
    # Disable reloader for stability, especially on macOS
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)