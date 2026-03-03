from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Thread
import time
import datetime
import numpy as np

from preprocess.stock_data import fetch_and_store_stock, load_stock_from_db
from preprocess.feature_engineering import create_features, fit_scaler
from preprocess.news_data import get_news

from ml.anomaly_model import train_anomaly, anomaly_probability
from ml.lstm_model import train_lstm, load_lstm, predict_lstm
from ml.bert_model import FinBERT
from ml.risk_engine import train_risk_model, load_risk_model
from ml.evaluation import evaluate_model

from config import SYMBOLS
from database.mongo import logs

import torch
torch.backends.cudnn.benchmark = True

# ==========================================================
# APP INIT
# ==========================================================

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bert = FinBERT()

models = {}
scalers = {}
lstm_models = {}
risk_model = None

# ==========================================================
# GLOBAL CACHES
# ==========================================================

dashboard_cache = {}
heatmap_cache = {}

# ==========================================================
# INITIAL DATA FETCH
# ==========================================================

def initialize_data():
    print("📥 Fetching stock data...")
    for symbol in SYMBOLS:
        fetch_and_store_stock(symbol)
    print("✅ Stock data ready")


# ==========================================================
# TRAIN BASE MODELS
# ==========================================================

def train_all():
    print("🔄 Training base models...")

    for symbol in SYMBOLS:

        df = load_stock_from_db(symbol)
        if df.empty:
            continue

        X = create_features(df, symbol=symbol, store=True)

        scaler = fit_scaler(X, symbol)
        scalers[symbol] = scaler

        X_scaled = scaler.transform(X)
        models[symbol] = train_anomaly(X_scaled, symbol)

        train_lstm(X, symbol)
        lstm_models[symbol] = load_lstm(symbol)

    print("✅ Base models trained")


# ==========================================================
# TRAIN RISK MODEL
# ==========================================================

def train_risk():

    print("🔄 Training risk model...")

    training_data = []
    labels = []

    for symbol in SYMBOLS:

        if symbol not in scalers:
            continue

        df = load_stock_from_db(symbol)
        if df.empty:
            continue

        X = create_features(df, symbol=symbol, store=False)
        X_scaled = scalers[symbol].transform(X)

        anomaly_probs = anomaly_probability(models[symbol], X_scaled)

        current_price = df["Close"].iloc[-1]
        lstm_pred = predict_lstm(lstm_models[symbol], df, symbol)
        lstm_deviation = abs(current_price - lstm_pred) / current_price

        news = get_news(symbol)
        sentiment_score = 0.5

        if news:
            result = bert.sentiment(news[0]["title"])
            sentiment_score = float(result[2])

        for prob in anomaly_probs:
            training_data.append([prob, sentiment_score, lstm_deviation])
            labels.append(1 if prob > 0.7 else 0)

    if training_data:
        X_train = np.array(training_data)
        y_train = np.array(labels)
        train_risk_model(X_train, y_train)

    print("✅ Risk model trained")


# ==========================================================
# CORE COMPUTE FUNCTION
# ==========================================================

def compute_symbol(symbol):

    df = load_stock_from_db(symbol)
    if df.empty:
        return None

    X = create_features(df)
    X_scaled = scalers[symbol].transform(X)

    anomaly_probs = anomaly_probability(models[symbol], X_scaled)
    latest_anomaly = float(anomaly_probs[-1])

    current_price = df["Close"].iloc[-1]
    lstm_pred = predict_lstm(lstm_models[symbol], df, symbol)
    lstm_deviation = abs(current_price - lstm_pred) / current_price

    news = get_news(symbol)
    sentiment_score = 0.5
    news_list = []

    if news:
        for item in news[:5]:
            result = bert.sentiment(item["title"])
            score = float(result[2])
            news_list.append({
                "title": item["title"],
                "sentiment": score
            })
        sentiment_score = news_list[0]["sentiment"]

    risk = (
        0.5 * lstm_deviation +
        0.3 * latest_anomaly +
        0.2 * abs(sentiment_score)
    )

    risk = min(risk * 10, 10)

    # Store risk in MongoDB
    logs.insert_one({
        "symbol": symbol,
        "risk": float(risk),
        "timestamp": datetime.datetime.utcnow()
    })

    risk_history = list(
        logs.find({"symbol": symbol})
        .sort("timestamp", -1)
        .limit(20)
    )

    risk_values = [float(r["risk"]) for r in risk_history]
    # Calculate daily returns
    returns = df["Close"].pct_change().dropna()

    # Annualized volatility (simple)
    volatility = float(returns.std() * np.sqrt(252) * 100)

    # 🔥 FIX: Convert Date column before JSON serialization
    df_tail = df.tail(40).copy()

    if "Date" in df_tail.columns:
        df_tail["Date"] = df_tail["Date"].astype(str)

    ohlc_records = df_tail.to_dict(orient="records")

    return {
        "symbol": symbol,
        "anomaly_probability": latest_anomaly,
        "risk_score": float(risk),
        "sentiment_score": float(sentiment_score),
        "lstm_deviation": float(lstm_deviation),
        "lstm_prediction": float(lstm_pred),
        "risk_history": risk_values[::-1],
        "ohlc": ohlc_records,
        "volatility": volatility,
        "news": news_list
    }


# ==========================================================
# BACKGROUND ML ENGINE
# ==========================================================

def background_risk_engine():

    print("🚀 Background risk engine started")

    while True:

        for symbol in SYMBOLS:
            try:
                result = compute_symbol(symbol)

                if result:
                    dashboard_cache[symbol] = result
                    heatmap_cache[symbol] = result["risk_score"]

            except Exception as e:
                print("❌ Error computing", symbol, e)

        # Emit full heatmap update
        socketio.emit("heatmap_update", heatmap_cache)

        print("✅ Cache refreshed")
        time.sleep(300)   # 🔥 Every 5 minutes


# ==========================================================
# HOME
# ==========================================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/heatmap")
def heatmap():
    data = []

    for symbol, risk in heatmap_cache.items():
        data.append({
            "symbol": symbol,
            "risk_score": float(risk)
        })

    return data


# ==========================================================
# SOCKET EVENTS
# ==========================================================

@socketio.on("request_dashboard")
def handle_dashboard_request(data):

    symbol = data.get("symbol", "AAPL")

    if symbol in dashboard_cache:
        socketio.emit("dashboard_update",
                      dashboard_cache[symbol])


# ==========================================================
# STARTUP PIPELINE
# ==========================================================

initialize_data()
train_all()
train_risk()
risk_model = load_risk_model()


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    worker = Thread(target=background_risk_engine)
    worker.daemon = True
    worker.start()

    socketio.run(app, debug=False, use_reloader=False)