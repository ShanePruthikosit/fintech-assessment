"""
SimuVest Backend API
FastAPI-based trading simulation engine
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import sqlite3
import uuid
from datetime import datetime
import json
from contextlib import contextmanager

app = FastAPI(title="SimuVest API", version="1.0")

# CORS configuration for frontend
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
    type: str  # 'BUY' or 'SELL'
    quantity: int
    orderType: str = "MARKET"  # 'MARKET' or 'LIMIT'
    limitPrice: Optional[float] = None

class UserCreate(BaseModel):
    userId: str
    initialCapital: float = 100000.0

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
    """Initialize database schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                initial_capital REAL NOT NULL,
                current_cash REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table (ledger)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
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
        
        conn.commit()
    finally:
        conn.close()

# Initialize DB on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("✓ Database initialized")

# Market data simulation
MARKET_DATA = {
    "AAPL": {"name": "Apple Inc.", "price": 189.50, "change": 2.3},
    "GOOGL": {"name": "Alphabet Inc.", "price": 142.80, "change": -0.8},
    "MSFT": {"name": "Microsoft Corp.", "price": 378.25, "change": 1.5},
    "AMZN": {"name": "Amazon.com Inc.", "price": 151.75, "change": 3.2},
    "TSLA": {"name": "Tesla Inc.", "price": 238.45, "change": -1.2},
    "NVDA": {"name": "NVIDIA Corp.", "price": 495.80, "change": 4.5},
    "META": {"name": "Meta Platforms", "price": 355.20, "change": 1.8},
    "NFLX": {"name": "Netflix Inc.", "price": 485.30, "change": -0.5},
}

@app.get("/")
async def root():
    return {"message": "SimuVest API v1.0", "status": "operational"}

@app.get("/api/market/stocks")
async def get_stocks():
    """Get list of available stocks with current prices"""
    return {"stocks": MARKET_DATA}

@app.get("/api/market/stock/{symbol}")
async def get_stock(symbol: str):
    """Get specific stock data"""
    symbol = symbol.upper()
    if symbol not in MARKET_DATA:
        raise HTTPException(status_code=404, detail="Stock not found")
    return MARKET_DATA[symbol]

@app.post("/api/users")
async def create_user(user: UserCreate):
    """Create new user with initial capital"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user.userId,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create user
        cursor.execute("""
            INSERT INTO users (user_id, initial_capital, current_cash)
            VALUES (?, ?, ?)
        """, (user.userId, user.initialCapital, user.initialCapital))
        
        return {
            "userId": user.userId,
            "initialCapital": user.initialCapital,
            "currentCash": user.initialCapital
        }

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get user information"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "userId": user["user_id"],
            "initialCapital": user["initial_capital"],
            "currentCash": user["current_cash"]
        }

@app.get("/api/portfolio/{user_id}")
async def get_portfolio(user_id: str):
    """Get user's portfolio with holdings and metrics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get user
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get holdings
        cursor.execute("""
            SELECT symbol, quantity, average_cost
            FROM holdings
            WHERE user_id = ? AND quantity > 0
        """, (user_id,))
        
        holdings = []
        total_holdings_value = 0
        
        for row in cursor.fetchall():
            symbol = row["symbol"]
            quantity = row["quantity"]
            avg_cost = row["average_cost"]
            current_price = MARKET_DATA.get(symbol, {}).get("price", 0)
            
            current_value = quantity * current_price
            total_cost = quantity * avg_cost
            gain_loss = current_value - total_cost
            gain_loss_pct = (gain_loss / total_cost * 100) if total_cost > 0 else 0
            
            holdings.append({
                "symbol": symbol,
                "name": MARKET_DATA.get(symbol, {}).get("name", symbol),
                "quantity": quantity,
                "averageCost": avg_cost,
                "currentPrice": current_price,
                "currentValue": current_value,
                "gainLoss": gain_loss,
                "gainLossPct": gain_loss_pct
            })
            
            total_holdings_value += current_value
        
        current_cash = user["current_cash"]
        total_value = current_cash + total_holdings_value
        initial_capital = user["initial_capital"]
        total_gain_loss = total_value - initial_capital
        total_gain_loss_pct = (total_gain_loss / initial_capital * 100) if initial_capital > 0 else 0
        
        return {
            "userId": user_id,
            "currentCash": current_cash,
            "totalValue": total_value,
            "totalGainLoss": total_gain_loss,
            "totalGainLossPct": total_gain_loss_pct,
            "holdings": holdings
        }

@app.get("/api/transactions/{user_id}")
async def get_transactions(user_id: str, limit: int = 50):
    """Get user's transaction history"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_id, type, symbol, price, quantity, timestamp
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
                "timestamp": row["timestamp"]
            })
        
        return {"transactions": transactions}

@app.post("/api/trade")
async def execute_trade(trade: TradeRequest):
    """Execute a trade (buy or sell)"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get user
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (trade.userId,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get stock price
        if trade.symbol not in MARKET_DATA:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        current_price = MARKET_DATA[trade.symbol]["price"]
        execution_price = trade.limitPrice if trade.orderType == "LIMIT" else current_price
        
        # Validate trade
        if trade.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        current_cash = user["current_cash"]
        
        if trade.type == "BUY":
            total_cost = execution_price * trade.quantity
            if total_cost > current_cash:
                raise HTTPException(status_code=400, detail="Insufficient funds")
            
            # Update cash
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
            # Check holdings
            cursor.execute("""
                SELECT quantity FROM holdings 
                WHERE user_id = ? AND symbol = ?
            """, (trade.userId, trade.symbol))
            
            holding = cursor.fetchone()
            if not holding or holding["quantity"] < trade.quantity:
                raise HTTPException(status_code=400, detail="Insufficient shares")
            
            # Update cash
            total_proceeds = execution_price * trade.quantity
            new_cash = current_cash + total_proceeds
            cursor.execute("UPDATE users SET current_cash = ? WHERE user_id = ?",
                         (new_cash, trade.userId))
            
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
        
        # Record transaction
        transaction_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO transactions (transaction_id, user_id, type, symbol, price, quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (transaction_id, trade.userId, trade.type, trade.symbol, execution_price, trade.quantity))
        
        return {
            "transactionId": transaction_id,
            "type": trade.type,
            "symbol": trade.symbol,
            "price": execution_price,
            "quantity": trade.quantity,
            "status": "executed"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
