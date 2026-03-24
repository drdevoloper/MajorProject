import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

SYMBOLS = [
    "AAPL",
    "MSFT",
    "TSLA",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "IBM",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "WIPRO.NS",
    "ONGC.NS",
]