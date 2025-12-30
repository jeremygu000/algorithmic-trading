
import yfinance as yf
import json

def check_fundamentals(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Extract key fundamental metrics
        fundamentals = {
            "symbol": symbol,
            "peRatio": info.get("trailingPE"),
            "pegRatio": info.get("pegRatio"),
            "pbRatio": info.get("priceToBook"),
            "trailingEPS": info.get("trailingEps"),
            "marketCap": info.get("marketCap"),
            "sector": info.get("sector")
        }
        
        print(json.dumps(fundamentals, indent=2))
        return fundamentals
    except Exception as e:
        print(f"Error checking {symbol}: {str(e)}")

if __name__ == "__main__":
    check_fundamentals("AAPL")
