import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib
import os
from database.mongo import db

# =====================================================
# CONFIG
# =====================================================

MODEL_DIR = "models/scalers"
os.makedirs(MODEL_DIR, exist_ok=True)

features_collection = db["features"]

# Create compound index (avoid duplicates)
features_collection.create_index(
    [("symbol", 1), ("Date", 1)],
    unique=True
)

# =====================================================
# CREATE FEATURES + STORE IN MONGODB
# =====================================================

def create_features(df, symbol=None, store=True):

    if df is None or df.empty:
        print("⚠ Empty dataframe passed to create_features()")
        return pd.DataFrame()

    df = df.copy()

    # -------------------------------------------------
    # Ensure Date exists (index → column)
    # -------------------------------------------------
    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()

    if "Date" not in df.columns:
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)

    # -------------------------------------------------
    # Feature Engineering
    # -------------------------------------------------

    df["returns"] = df["Close"].pct_change()
    df["log_returns"] = np.log(df["Close"] / df["Close"].shift(1))

    df["spread"] = df["High"] - df["Low"]

    df["rolling_mean_5"] = df["Close"].rolling(5).mean()
    df["rolling_std_5"] = df["Close"].rolling(5).std()

    df["rolling_mean_15"] = df["Close"].rolling(15).mean()
    df["rolling_std_15"] = df["Close"].rolling(15).std()

    df["volume_change"] = df["Volume"].pct_change()
    df["volume_ma_10"] = df["Volume"].rolling(10).mean()

    df["volume_zscore"] = (
        (df["Volume"] - df["Volume"].rolling(20).mean()) /
        df["Volume"].rolling(20).std()
    )

    # -------------------------------------------------
    # Clean infinities BEFORE selecting numeric columns
    # -------------------------------------------------

    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Forward + backward fill
    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Final safety fill
    df.fillna(0, inplace=True)

    # -------------------------------------------------
    # Select numeric features only
    # -------------------------------------------------

    feature_df = df.select_dtypes(include=np.number)

    # Final safety cleaning
    feature_df = feature_df.replace([np.inf, -np.inf], 0)
    feature_df = feature_df.fillna(0)

    print("Symbol:", symbol)
    print("Store flag:", store)
    print("Feature rows:", len(feature_df))

    # -------------------------------------------------
    # STORE FEATURES IN MONGODB
    # -------------------------------------------------

    if store and symbol is not None:

        try:
            records_df = feature_df.copy()
            records_df["Date"] = df["Date"].astype(str)
            records_df["symbol"] = symbol

            records = records_df.to_dict("records")

            if records:
                features_collection.delete_many({"symbol": symbol})
                features_collection.insert_many(records)
                print(f"✅ Features stored in MongoDB for {symbol}")
            else:
                print(f"⚠ No feature records generated for {symbol}")

        except Exception as e:
            print(f"❌ Mongo insert error for {symbol}: {e}")

    return feature_df

    

# =====================================================
# LOAD FEATURES FROM MONGO
# =====================================================

def load_features_from_db(symbol):

    try:
        data = list(features_collection.find({"symbol": symbol}))

        if not data:
            print(f"⚠ No feature data found in DB for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df.drop(columns=["_id"], inplace=True)

        return df.select_dtypes(include=np.number)

    except Exception as e:
        print(f"❌ Error loading features for {symbol}: {e}")
        return pd.DataFrame()


# =====================================================
# SCALER
# =====================================================

def fit_scaler(X, symbol):

    import numpy as np
    from sklearn.preprocessing import StandardScaler

    # 🔥 Replace infinities
    X = np.where(np.isinf(X), np.nan, X)

    # 🔥 Replace NaN with column mean
    col_means = np.nanmean(X, axis=0)
    inds = np.where(np.isnan(X))
    X[inds] = np.take(col_means, inds[1])

    # 🔥 Clip extreme values (very important)
    X = np.clip(X, -1e6, 1e6)

    scaler = StandardScaler()
    scaler.fit(X)

    return scaler


def load_scaler(symbol):

    path = f"{MODEL_DIR}/{symbol}_scaler.pkl"

    if not os.path.exists(path):
        raise FileNotFoundError(f"No scaler found for {symbol}")

    return joblib.load(path)