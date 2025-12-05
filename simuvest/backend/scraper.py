"""
Market Data Scraper
Simulates web scraping for stock prices
In production, this would scrape real market data with time delay
"""
import requests
from bs4 import BeautifulSoup
import random
import time
from typing import Dict

class MarketDataScraper:
    """Simulated market data scraper"""
    
    def __init__(self):
        self.base_prices = {
            "AAPL": 189.50,
            "GOOGL": 142.80,
            "MSFT": 378.25,
            "AMZN": 151.75,
            "TSLA": 238.45,
            "NVDA": 495.80,
            "META": 355.20,
            "NFLX": 485.30,
        }
    
    def scrape_stock_price(self, symbol: str) -> Dict:
        """
        Simulate scraping stock price from a financial website
        In production: Would scrape from Yahoo Finance, Google Finance, etc.
        """
        # Simulate network delay
        time.sleep(0.1)
        
        if symbol not in self.base_prices:
            return None
        
        # Simulate price fluctuation
        base_price = self.base_prices[symbol]
        fluctuation = random.uniform(-0.03, 0.03)  # ±3%
        current_price = base_price * (1 + fluctuation)
        change_pct = fluctuation * 100
        
        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "change": round(change_pct, 2),
            "timestamp": time.time()
        }
    
    def scrape_multiple_stocks(self, symbols: list) -> Dict:
        """Scrape prices for multiple stocks"""
        results = {}
        for symbol in symbols:
            data = self.scrape_stock_price(symbol)
            if data:
                results[symbol] = data
        return results
    
    def scrape_yahoo_finance(self, symbol: str) -> Dict:
        """
        Example of real scraping (disabled for demo)
        Would scrape from Yahoo Finance with proper error handling
        """
        # DEMO ONLY - Real implementation would:
        # 1. Make request to Yahoo Finance
        # 2. Parse HTML with BeautifulSoup
        # 3. Extract price data
        # 4. Handle errors and rate limiting
        
        # url = f"https://finance.yahoo.com/quote/{symbol}"
        # headers = {'User-Agent': 'Mozilla/5.0'}
        # response = requests.get(url, headers=headers)
        # soup = BeautifulSoup(response.text, 'html.parser')
        # ... parsing logic ...
        
        pass

if __name__ == "__main__":
    scraper = MarketDataScraper()
    
    # Test scraping
    print("Testing market data scraper...")
    data = scraper.scrape_stock_price("AAPL")
    print(f"AAPL: ${data['price']} ({data['change']:+.2f}%)")
    
    # Test multiple stocks
    all_data = scraper.scrape_multiple_stocks(["AAPL", "GOOGL", "MSFT"])
    print(f"\nScraped {len(all_data)} stocks successfully")
