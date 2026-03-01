from database.mongo import stocks_collection
import pandas as pd
import yfinance as yf


def fetch_and_store_stock(symbol):

    df = yf.download(symbol, period="8mo", interval="1d", progress=False)

    if df.empty:
        return pd.DataFrame()

    # 🔥 FIX 1: Remove MultiIndex if exists
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df.reset_index(inplace=True)

    # 🔥 Ensure all column names are strings
    df.columns = [str(col) for col in df.columns]

    # 🔥 Convert datetime properly
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])

    records = df.to_dict("records")

    # 🔥 Remove old data for symbol
    stocks_collection.delete_many({"symbol": symbol})

    # Add symbol to each record
    for row in records:
        row["symbol"] = symbol

    stocks_collection.insert_many(records)

    return df

def load_stock_from_db(symbol):

    data = list(stocks_collection.find({"symbol": symbol}))

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    df.drop(columns=["_id"], inplace=True)

    return df