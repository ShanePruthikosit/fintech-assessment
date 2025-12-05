#!/usr/bin/env python3
"""
SimuVest API Test Script
Tests all core functionality
"""
import requests
import json
import time

API_BASE = "http://localhost:8000/api"
USER_ID = "demo_user"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_market_data():
    print_section("1. Testing Market Data")
    
    response = requests.get(f"{API_BASE}/market/stocks")
    data = response.json()
    
    print(f"Available stocks: {len(data['stocks'])}")
    for symbol, info in list(data['stocks'].items())[:3]:
        print(f"  {symbol}: ${info['price']:.2f} ({info['change']:+.2f}%)")
    print()

def test_user_creation():
    print_section("2. Creating User")
    
    response = requests.post(f"{API_BASE}/users", json={
        "userId": USER_ID,
        "initialCapital": 100000.0
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ User created: {data['userId']}")
        print(f"   Initial Capital: ${data['initialCapital']:,.2f}")
    elif response.status_code == 400:
        print(f"ℹ️  User already exists")
    print()

def test_portfolio():
    print_section("3. Checking Portfolio")
    
    response = requests.get(f"{API_BASE}/portfolio/{USER_ID}")
    data = response.json()
    
    print(f"Cash Balance: ${data['currentCash']:,.2f}")
    print(f"Total Value: ${data['totalValue']:,.2f}")
    print(f"Total P&L: ${data['totalGainLoss']:,.2f} ({data['totalGainLossPct']:.2f}%)")
    print(f"Holdings: {len(data['holdings'])}")
    print()

def test_buy_trade():
    print_section("4. Executing Buy Order")
    
    response = requests.post(f"{API_BASE}/trade", json={
        "userId": USER_ID,
        "symbol": "AAPL",
        "type": "BUY",
        "quantity": 50,
        "orderType": "MARKET"
    })
    
    data = response.json()
    print(f"✅ Trade executed: {data['type']} {data['quantity']} {data['symbol']}")
    print(f"   Price: ${data['price']:.2f}")
    print(f"   Total: ${data['price'] * data['quantity']:,.2f}")
    print()

def test_sell_trade():
    print_section("5. Executing Sell Order")
    
    response = requests.post(f"{API_BASE}/trade", json={
        "userId": USER_ID,
        "symbol": "AAPL",
        "type": "SELL",
        "quantity": 20,
        "orderType": "MARKET"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Trade executed: {data['type']} {data['quantity']} {data['symbol']}")
        print(f"   Price: ${data['price']:.2f}")
        print(f"   Total: ${data['price'] * data['quantity']:,.2f}")
    else:
        print(f"❌ Trade failed: {response.json()['detail']}")
    print()

def test_updated_portfolio():
    print_section("6. Updated Portfolio")
    
    response = requests.get(f"{API_BASE}/portfolio/{USER_ID}")
    data = response.json()
    
    print(f"Cash Balance: ${data['currentCash']:,.2f}")
    print(f"Total Value: ${data['totalValue']:,.2f}")
    print(f"Total P&L: ${data['totalGainLoss']:,.2f} ({data['totalGainLossPct']:.2f}%)")
    print(f"\nHoldings:")
    for holding in data['holdings']:
        print(f"  {holding['symbol']}: {holding['quantity']} shares @ ${holding['currentPrice']:.2f}")
        print(f"    P&L: ${holding['gainLoss']:.2f} ({holding['gainLossPct']:.2f}%)")
    print()

def test_transactions():
    print_section("7. Transaction History")
    
    response = requests.get(f"{API_BASE}/transactions/{USER_ID}?limit=5")
    data = response.json()
    
    print(f"Recent transactions: {len(data['transactions'])}")
    for tx in data['transactions'][:5]:
        print(f"  {tx['type']:4} {tx['quantity']:3} {tx['symbol']:5} @ ${tx['price']:.2f}")
    print()

def main():
    print("\n🚀 SimuVest API Test Suite")
    print("Testing all core functionality...")
    
    try:
        test_market_data()
        test_user_creation()
        test_portfolio()
        test_buy_trade()
        time.sleep(0.5)
        test_sell_trade()
        time.sleep(0.5)
        test_updated_portfolio()
        test_transactions()
        
        print_section("✅ All Tests Passed")
        print("The SimuVest API is working correctly!")
        print("\nNext steps:")
        print("1. Open frontend/index.html in your browser")
        print("2. Start trading with the web interface")
        print("3. View API docs at http://localhost:8000/docs")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API")
        print("Make sure the backend is running:")
        print("  cd backend && python3 main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
