import requests
import yfinance as yf
import socket
import ssl
from config import ALPHA_VANTAGE_KEY, FINNHUB_KEY


def test_yfinance():
    print("\n🔎 Testing yfinance...")
    try:
        df = yf.download("AAPL", period="5d")
        print("✅ yfinance working")
        print(df.head())
    except Exception as e:
        print("❌ yfinance failed:", e)


def test_alpha_vantage():
    print("\n🔎 Testing Alpha Vantage...")
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": "AAPL",
            "apikey": ALPHA_VANTAGE_KEY
        }

        r = requests.get(url, params=params, timeout=10)
        print("Status Code:", r.status_code)

        if r.status_code == 200:
            print("✅ Alpha Vantage working")
            print(r.json().get("Meta Data"))
        else:
            print("❌ Alpha Vantage error:", r.text)

    except Exception as e:
        print("❌ Alpha Vantage failed:", e)


def test_finnhub():
    print("\n🔎 Testing Finnhub...")
    try:
        url = "https://finnhub.io/api/v1/stock/candle"
        params = {
            "symbol": "AAPL",
            "resolution": "D",
            "count": 5,
            "token": FINNHUB_KEY
        }

        r = requests.get(url, params=params, timeout=10)
        print("Status Code:", r.status_code)

        if r.status_code == 200:
            print("✅ Finnhub working")
            print(r.json())
        else:
            print("❌ Finnhub error:", r.text)

    except Exception as e:
        print("❌ Finnhub failed:", e)


def test_ssl_connection():
    print("\n🔎 Testing raw SSL connection...")
    try:
        hostname = "finnhub.io"
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                print("✅ SSL handshake successful with finnhub.io")
    except Exception as e:
        print("❌ SSL handshake failed:", e)


if __name__ == "__main__":
    test_ssl_connection()
    test_yfinance()
    test_alpha_vantage()
    test_finnhub()