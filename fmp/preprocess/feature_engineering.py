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
    # Ensure Date exists
    # -------------------------------------------------

    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()

    if "Date" not in df.columns:
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)

    # -------------------------------------------------
    # Feature Engineering
    # -------------------------------------------------

    # Returns
    df["returns"] = df["Close"].pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)

    # Log returns
    price_ratio = df["Close"] / df["Close"].shift(1).replace(0, np.nan)
    price_ratio = price_ratio.clip(0.0001, 1000)
    df["log_returns"] = np.log(price_ratio)

    # Volatility
    df["volatility"] = df["returns"].rolling(10).std()

    # Spread
    df["spread"] = df["High"] - df["Low"]
 
    # Rolling statistics
    df["rolling_mean_5"] = df["Close"].rolling(5).mean()
    df["rolling_std_5"] = df["Close"].rolling(5).std().replace(0, np.nan)

    df["rolling_mean_15"] = df["Close"].rolling(15).mean()
    df["rolling_std_15"] = df["Close"].rolling(15).std().replace(0, np.nan)

    # Volume features
    df["volume_change"] = df["Volume"].pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)

    df["volume_ma_10"] = df["Volume"].rolling(10).mean()

    vol_std = df["Volume"].rolling(20).std().replace(0, np.nan)

    df["volume_zscore"] = (
       (df["Volume"] - df["Volume"].rolling(20).mean()) /
       vol_std
    )

    # ---------------------------------------
    # Handle NaN values WITHOUT dropping rows
    # ---------------------------------------

    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    df.ffill(inplace=True)   # forward fill
    df.bfill(inplace=True)   # backward fill

    df.fillna(0, inplace=True)

    # -------------------------------------------------
    # Select only required ML features
    # -------------------------------------------------

    feature_columns = [

        "Close",
        "High",
        "Low",
        "Open",
        "Volume",

        "returns",
        "log_returns",
        "spread",

        "rolling_mean_5",
        "rolling_std_5",

        "rolling_mean_15",
        "rolling_std_15",

        "volume_change",
        "volume_ma_10",
        "volume_zscore",

        "volatility"
    ]

    feature_df = df[feature_columns]

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

    X = np.where(np.isinf(X), np.nan, X)

    col_means = np.nanmean(X, axis=0)

    inds = np.where(np.isnan(X))

    X[inds] = np.take(col_means, inds[1])

    X = np.clip(X, -1e6, 1e6)

    scaler = StandardScaler()

    scaler.fit(X)

    path = f"{MODEL_DIR}/{symbol}_scaler.pkl"

    joblib.dump(scaler, path)

    return scaler


def load_scaler(symbol):

    path = f"{MODEL_DIR}/{symbol}_scaler.pkl"

    if not os.path.exists(path):

        raise FileNotFoundError(f"No scaler found for {symbol}")

    return joblib.load(path)