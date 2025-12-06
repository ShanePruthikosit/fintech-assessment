"""
SimuVest Backend API v2.0
FastAPI-based trading simulation engine with real-time stock prices
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import sqlite3
import uuid
from datetime import datetime, timedelta
import json
from contextlib import contextmanager
import asyncio
import requests
import time
import random

app = FastAPI(title="SimuVest API", version="2.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
import os
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "simuvest.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Pydantic models
class TradeRequest(BaseModel):
    userId: str
    symbol: str
    type: str
    quantity: int
    orderType: str = "MARKET"
    limitPrice: Optional[float] = None

class UserCreate(BaseModel):
    userId: str
    initialCapital: float = 100000.0

# Global stock price cache
STOCK_PRICES = {}
LAST_UPDATE = None
UPDATE_INTERVAL = 60  # Update every 60 seconds

# Stock symbols to track
TRACKED_STOCKS = {
    "AAPL": "Apple Inc.",
    "GOOGL": "Alphabet Inc.",
    "MSFT": "Microsoft Corp.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "NVDA": "NVIDIA Corp.",
    "META": "Meta Platforms",
    "NFLX": "Netflix Inc.",
}

@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize database schema with earnings tracking"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Users table with earnings tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                initial_capital REAL NOT NULL,
                current_cash REAL NOT NULL,
                total_realized_gains REAL DEFAULT 0,
                total_unrealized_gains REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                realized_gain REAL DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Holdings cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                average_cost REAL NOT NULL,
                PRIMARY KEY (user_id, symbol),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Price history table for tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                change_pct REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timestamp)
            )
        """)
        
        conn.commit()
    finally:
        conn.close()

def fetch_real_stock_price(symbol: str) -> Optional[Dict]:
    """
    Fetch real stock price from Yahoo Finance
    Falls back to simulated data if fetch fails
    """
    try:
        # Yahoo Finance API endpoint
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": "1m",
            "range": "1d"
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            chart = data.get('chart', {}).get('result', [{}])[0]
            meta = chart.get('meta', {})
            
            current_price = meta.get('regularMarketPrice')
            previous_close = meta.get('previousClose')
            
            if current_price and previous_close:
                change_pct = ((current_price - previous_close) / previous_close) * 100
                return {
                    "price": round(current_price, 2),
                    "change": round(change_pct, 2),
                    "source": "yahoo_finance"
                }
    except Exception as e:
        print(f"Failed to fetch {symbol}: {e}")
    
    # Fallback to simulated data
    return None

def update_stock_prices():
    """Update all stock prices from real market data"""
    global STOCK_PRICES, LAST_UPDATE
    
    print("Updating stock prices...")
    
    for symbol, name in TRACKED_STOCKS.items():
        # Try to fetch real price
        real_data = fetch_real_stock_price(symbol)
        
        if real_data:
            STOCK_PRICES[symbol] = {
                "name": name,
                "price": real_data["price"],
                "change": real_data["change"],
                "source": "live"
            }
        else:
            # Use last known price or simulate
            if symbol in STOCK_PRICES:
                old_price = STOCK_PRICES[symbol]["price"]
                # Small random fluctuation
                fluctuation = random.uniform(-0.02, 0.02)
                new_price = old_price * (1 + fluctuation)
                change_pct = fluctuation * 100
            else:
                # Initial prices
                base_prices = {
                    "AAPL": 189.50, "GOOGL": 142.80, "MSFT": 378.25,
                    "AMZN": 151.75, "TSLA": 238.45, "NVDA": 495.80,
                    "META": 355.20, "NFLX": 485.30
                }
                new_price = base_prices.get(symbol, 100.0)
                change_pct = 0.0
            
            STOCK_PRICES[symbol] = {
                "name": name,
                "price": round(new_price, 2),
                "change": round(change_pct, 2),
                "source": "simulated"
            }
        
        # Store in price history
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO price_history (symbol, price, change_pct)
                    VALUES (?, ?, ?)
                """, (symbol, STOCK_PRICES[symbol]["price"], STOCK_PRICES[symbol]["change"]))
        except:
            pass
    
    LAST_UPDATE = datetime.now()
    print(f"Prices updated at {LAST_UPDATE}")

async def price_updater_task():
    """Background task to update prices regularly"""
    while True:
        update_stock_prices()
        await asyncio.sleep(UPDATE_INTERVAL)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("✓ Database initialized")
    
    # Initial price fetch
    update_stock_prices()
    
    # Start background price updater
    asyncio.create_task(price_updater_task())
    print("✓ Price updater started")

@app.get("/")
async def root():
    return {
        "message": "SimuVest API v2.0",
        "status": "operational",
        "last_update": LAST_UPDATE.isoformat() if LAST_UPDATE else None
    }

@app.get("/api/market/stocks")
async def get_stocks():
    """Get list of available stocks with current prices"""
    return {"stocks": STOCK_PRICES, "last_update": LAST_UPDATE.isoformat() if LAST_UPDATE else None}

@app.get("/api/market/stock/{symbol}")
async def get_stock(symbol: str):
    """Get specific stock data"""
    symbol = symbol.upper()
    if symbol not in STOCK_PRICES:
        raise HTTPException(status_code=404, detail="Stock not found")
    return STOCK_PRICES[symbol]

@app.post("/api/users")
async def create_user(user: UserCreate):
    """Create new user with initial capital"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user.userId,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")
        
        cursor.execute("""
            INSERT INTO users (user_id, initial_capital, current_cash, total_realized_gains, total_unrealized_gains)
            VALUES (?, ?, ?, 0, 0)
        """, (user.userId, user.initialCapital, user.initialCapital))
        
        return {
            "userId": user.userId,
            "initialCapital": user.initialCapital,
            "currentCash": user.initialCapital
        }

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get user information with earnings"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "userId": user["user_id"],
            "initialCapital": user["initial_capital"],
            "currentCash": user["current_cash"],
            "totalRealizedGains": user["total_realized_gains"],
            "totalUnrealizedGains": user["total_unrealized_gains"]
        }

@app.get("/api/portfolio/{user_id}")
async def get_portfolio(user_id: str):
    """Get user's portfolio with holdings and detailed earnings metrics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        cursor.execute("""
            SELECT symbol, quantity, average_cost
            FROM holdings
            WHERE user_id = ? AND quantity > 0
        """, (user_id,))
        
        holdings = []
        total_holdings_value = 0
        total_unrealized_gains = 0
        
        for row in cursor.fetchall():
            symbol = row["symbol"]
            quantity = row["quantity"]
            avg_cost = row["average_cost"]
            current_price = STOCK_PRICES.get(symbol, {}).get("price", 0)
            
            current_value = quantity * current_price
            total_cost = quantity * avg_cost
            unrealized_gain = current_value - total_cost
            unrealized_gain_pct = (unrealized_gain / total_cost * 100) if total_cost > 0 else 0
            
            holdings.append({
                "symbol": symbol,
                "name": STOCK_PRICES.get(symbol, {}).get("name", symbol),
                "quantity": quantity,
                "averageCost": avg_cost,
                "currentPrice": current_price,
                "currentValue": current_value,
                "totalCost": total_cost,
                "unrealizedGain": unrealized_gain,
                "unrealizedGainPct": unrealized_gain_pct,
                # Keep old names for compatibility
                "gainLoss": unrealized_gain,
                "gainLossPct": unrealized_gain_pct
            })
            
            total_holdings_value += current_value
            total_unrealized_gains += unrealized_gain
        
        current_cash = user["current_cash"]
        total_value = current_cash + total_holdings_value
        initial_capital = user["initial_capital"]
        total_realized_gains = user["total_realized_gains"]
        
        # Total profit = realized + unrealized
        total_profit = total_realized_gains + total_unrealized_gains
        total_profit_pct = (total_profit / initial_capital * 100) if initial_capital > 0 else 0
        
        # Update unrealized gains in database
        cursor.execute("""
            UPDATE users SET total_unrealized_gains = ?
            WHERE user_id = ?
        """, (total_unrealized_gains, user_id))
        
        return {
            "userId": user_id,
            "currentCash": current_cash,
            "totalValue": total_value,
            "totalGainLoss": total_profit,  # For compatibility
            "totalGainLossPct": total_profit_pct,  # For compatibility
            "totalRealizedGains": total_realized_gains,
            "totalUnrealizedGains": total_unrealized_gains,
            "totalProfit": total_profit,
            "totalProfitPct": total_profit_pct,
            "holdings": holdings
        }

@app.get("/api/transactions/{user_id}")
async def get_transactions(user_id: str, limit: int = 50):
    """Get user's transaction history with realized gains"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_id, type, symbol, price, quantity, realized_gain, timestamp
            FROM transactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                "transactionId": row["transaction_id"],
                "type": row["type"],
                "symbol": row["symbol"],
                "price": row["price"],
                "quantity": row["quantity"],
                "realizedGain": row["realized_gain"],
                "timestamp": row["timestamp"]
            })
        
        return {"transactions": transactions}

@app.post("/api/trade")
async def execute_trade(trade: TradeRequest):
    """Execute a trade with realized gains tracking"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (trade.userId,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if trade.symbol not in STOCK_PRICES:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        current_price = STOCK_PRICES[trade.symbol]["price"]
        execution_price = trade.limitPrice if trade.orderType == "LIMIT" else current_price
        
        if trade.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        current_cash = user["current_cash"]
        realized_gain = 0.0
        
        if trade.type == "BUY":
            total_cost = execution_price * trade.quantity
            if total_cost > current_cash:
                raise HTTPException(status_code=400, detail="Insufficient funds")
            
            new_cash = current_cash - total_cost
            cursor.execute("UPDATE users SET current_cash = ? WHERE user_id = ?", 
                         (new_cash, trade.userId))
            
            # Update holdings
            cursor.execute("""
                SELECT quantity, average_cost FROM holdings 
                WHERE user_id = ? AND symbol = ?
            """, (trade.userId, trade.symbol))
            
            holding = cursor.fetchone()
            if holding:
                old_qty = holding["quantity"]
                old_avg = holding["average_cost"]
                new_qty = old_qty + trade.quantity
                new_avg = ((old_qty * old_avg) + (trade.quantity * execution_price)) / new_qty
                
                cursor.execute("""
                    UPDATE holdings 
                    SET quantity = ?, average_cost = ?
                    WHERE user_id = ? AND symbol = ?
                """, (new_qty, new_avg, trade.userId, trade.symbol))
            else:
                cursor.execute("""
                    INSERT INTO holdings (user_id, symbol, quantity, average_cost)
                    VALUES (?, ?, ?, ?)
                """, (trade.userId, trade.symbol, trade.quantity, execution_price))
        
        elif trade.type == "SELL":
            cursor.execute("""
                SELECT quantity, average_cost FROM holdings 
                WHERE user_id = ? AND symbol = ?
            """, (trade.userId, trade.symbol))
            
            holding = cursor.fetchone()
            if not holding or holding["quantity"] < trade.quantity:
                raise HTTPException(status_code=400, detail="Insufficient shares")
            
            # Calculate realized gain
            avg_cost = holding["average_cost"]
            realized_gain = (execution_price - avg_cost) * trade.quantity
            
            # Update cash
            total_proceeds = execution_price * trade.quantity
            new_cash = current_cash + total_proceeds
            cursor.execute("UPDATE users SET current_cash = ?, total_realized_gains = total_realized_gains + ? WHERE user_id = ?",
                         (new_cash, realized_gain, trade.userId))
            
            # Update holdings
            new_qty = holding["quantity"] - trade.quantity
            if new_qty > 0:
                cursor.execute("""
                    UPDATE holdings SET quantity = ?
                    WHERE user_id = ? AND symbol = ?
                """, (new_qty, trade.userId, trade.symbol))
            else:
                cursor.execute("""
                    DELETE FROM holdings
                    WHERE user_id = ? AND symbol = ?
                """, (trade.userId, trade.symbol))
        else:
            raise HTTPException(status_code=400, detail="Invalid trade type")
        
        # Record transaction with realized gain
        transaction_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO transactions (transaction_id, user_id, type, symbol, price, quantity, realized_gain)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (transaction_id, trade.userId, trade.type, trade.symbol, execution_price, trade.quantity, realized_gain))
        
        return {
            "transactionId": transaction_id,
            "type": trade.type,
            "symbol": trade.symbol,
            "price": execution_price,
            "quantity": trade.quantity,
            "realizedGain": realized_gain,
            "status": "executed"
        }

@app.get("/api/earnings/{user_id}")
async def get_earnings_summary(user_id: str):
    """Get detailed earnings breakdown"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get unrealized gains from holdings
        cursor.execute("""
            SELECT symbol, quantity, average_cost FROM holdings
            WHERE user_id = ? AND quantity > 0
        """, (user_id,))
        
        total_unrealized = 0
        for row in cursor.fetchall():
            current_price = STOCK_PRICES.get(row["symbol"], {}).get("price", 0)
            unrealized = (current_price - row["average_cost"]) * row["quantity"]
            total_unrealized += unrealized
        
        realized = user["total_realized_gains"]
        total_profit = realized + total_unrealized
        initial = user["initial_capital"]
        
        return {
            "userId": user_id,
            "initialCapital": initial,
            "totalRealizedGains": realized,
            "totalUnrealizedGains": total_unrealized,
            "totalProfit": total_profit,
            "returnOnInvestment": (total_profit / initial * 100) if initial > 0 else 0
        }

@app.post("/api/analysis/{user_id}")
async def get_ai_analysis(user_id: str):
    """Get AI-powered portfolio analysis using Claude API"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get user data
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get holdings
        cursor.execute("""
            SELECT symbol, quantity, average_cost FROM holdings
            WHERE user_id = ? AND quantity > 0
        """, (user_id,))
        holdings = cursor.fetchall()
        
        # Get recent transactions
        cursor.execute("""
            SELECT type, symbol, price, quantity, realized_gain, timestamp
            FROM transactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (user_id,))
        transactions = cursor.fetchall()
        
        # Calculate portfolio metrics
        total_unrealized = 0
        holdings_data = []
        for row in holdings:
            symbol = row["symbol"]
            quantity = row["quantity"]
            avg_cost = row["average_cost"]
            current_price = STOCK_PRICES.get(symbol, {}).get("price", 0)
            unrealized_gain = (current_price - avg_cost) * quantity
            unrealized_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0
            
            holdings_data.append({
                "symbol": symbol,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "unrealized_gain": unrealized_gain,
                "unrealized_pct": unrealized_pct,
                "position_value": current_price * quantity
            })
            total_unrealized += unrealized_gain
        
        # Prepare data for AI
        portfolio_summary = {
            "initial_capital": user["initial_capital"],
            "current_cash": user["current_cash"],
            "total_realized_gains": user["total_realized_gains"],
            "total_unrealized_gains": total_unrealized,
            "total_profit": user["total_realized_gains"] + total_unrealized,
            "roi_pct": ((user["total_realized_gains"] + total_unrealized) / user["initial_capital"] * 100) if user["initial_capital"] > 0 else 0,
            "holdings": holdings_data,
            "recent_transactions": [
                {
                    "type": tx["type"],
                    "symbol": tx["symbol"],
                    "price": tx["price"],
                    "quantity": tx["quantity"],
                    "realized_gain": tx["realized_gain"],
                    "timestamp": tx["timestamp"]
                } for tx in transactions
            ]
        }
        
        # Call Claude API
        try:
            analysis = await call_claude_api(portfolio_summary)
            return {
                "success": True,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "analysis": f"AI analysis temporarily unavailable. Here's a summary:\n\n"
                           f"Portfolio Value: ${user['current_cash'] + sum([h['position_value'] for h in holdings_data]):.2f}\n"
                           f"Total Profit: ${portfolio_summary['total_profit']:.2f} ({portfolio_summary['roi_pct']:.2f}% ROI)\n"
                           f"Realized Gains: ${user['total_realized_gains']:.2f}\n"
                           f"Unrealized Gains: ${total_unrealized:.2f}\n\n"
                           f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

async def call_claude_api(portfolio_data: dict) -> str:
    """Call Anthropic Claude API for portfolio analysis"""
    
    # Prepare the prompt
    prompt = f"""You are a professional financial advisor analyzing an investment portfolio. Provide detailed, actionable feedback.

Portfolio Summary:
- Initial Capital: ${portfolio_data['initial_capital']:,.2f}
- Current Cash: ${portfolio_data['current_cash']:,.2f}
- Total Profit/Loss: ${portfolio_data['total_profit']:,.2f} ({portfolio_data['roi_pct']:.2f}% ROI)
- Realized Gains: ${portfolio_data['total_realized_gains']:,.2f}
- Unrealized Gains: ${portfolio_data['total_unrealized_gains']:,.2f}

Current Holdings:
"""
    
    for holding in portfolio_data['holdings']:
        prompt += f"""
- {holding['symbol']}: {holding['quantity']} shares @ ${holding['avg_cost']:.2f} avg
  Current Price: ${holding['current_price']:.2f}
  Position Value: ${holding['position_value']:,.2f}
  Unrealized P&L: ${holding['unrealized_gain']:,.2f} ({holding['unrealized_pct']:.2f}%)
"""
    
    prompt += f"\n\nRecent Trading Activity ({len(portfolio_data['recent_transactions'])} transactions):\n"
    
    for tx in portfolio_data['recent_transactions'][:10]:
        gain_info = f" (Realized Gain: ${tx['realized_gain']:.2f})" if tx['type'] == 'SELL' else ""
        prompt += f"- {tx['timestamp']}: {tx['type']} {tx['quantity']} {tx['symbol']} @ ${tx['price']:.2f}{gain_info}\n"
    
    prompt += """

Please provide:
1. **Performance Assessment**: Evaluate the overall portfolio performance and ROI
2. **Risk Analysis**: Assess portfolio diversification and concentration risk
3. **Strengths**: What's working well in this portfolio
4. **Weaknesses**: Areas of concern or improvement
5. **Specific Recommendations**: 2-3 actionable suggestions for improvement
6. **Trading Pattern Analysis**: Comment on the trading behavior and strategy

Be concise but insightful. Use a professional yet encouraging tone."""
    
    # Call Claude API
    api_url = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "",  # API key handled by infrastructure
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        return result['content'][0]['text']
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
