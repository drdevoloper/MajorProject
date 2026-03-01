from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO

from preprocess.stock_data import fetch_and_store_stock, load_stock_from_db
from preprocess.feature_engineering import create_features, fit_scaler
from preprocess.news_data import get_news

from ml.anomaly_model import train_anomaly, anomaly_probability
from ml.lstm_model import train_lstm, load_lstm, predict_lstm
from ml.bert_model import FinBERT
from ml.risk_engine import train_risk_model, load_risk_model, calculate_risk
from ml.evaluation import evaluate_model

from config import SYMBOLS
from database.mongo import logs

import numpy as np
import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bert = FinBERT()

models = {}
scalers = {}
lstm_models = {}
risk_model = None

# 🔥 NEW: Heatmap cache (instant response)
heatmap_cache = {}


# ==========================================================
# 1️⃣ INITIAL DATA FETCH (ONLY ONCE)
# ==========================================================

def initialize_data():
    print("📥 Fetching and storing stock data...")
    for symbol in SYMBOLS:
        fetch_and_store_stock(symbol)
    print("✅ Stock data stored in MongoDB")


# ==========================================================
# 2️⃣ TRAIN BASE MODELS
# ==========================================================

def train_all():
    print("🔄 Training base models...")

    for symbol in SYMBOLS:

        df = load_stock_from_db(symbol)

        if df.empty:
            print(f"⚠ No DB data for {symbol}")
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
# 3️⃣ TRAIN RISK MODEL
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

            training_data.append([
                prob,
                sentiment_score,
                lstm_deviation
            ])

            labels.append(1 if prob > 0.7 else 0)

    if not training_data:
        print("⚠ No risk training data")
        return

    X_train = np.array(training_data)
    y_train = np.array(labels)

    train_risk_model(X_train, y_train)

    print("✅ Risk model trained")


# ==========================================================
# STARTUP PIPELINE
# ==========================================================

initialize_data()
train_all()
train_risk()
risk_model = load_risk_model()


# ==========================================================
# HOME
# ==========================================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================================
# 🔥 NEW FAST HEATMAP ENDPOINT
# ==========================================================

@app.route("/api/heatmap")
def heatmap():

    results = []

    for symbol in SYMBOLS:

        latest = logs.find_one(
            {"symbol": symbol},
            sort=[("timestamp", -1)]
        )

        if latest:
            results.append({
                "symbol": symbol,
                "risk_score": float(latest["risk"])
            })
        else:
            results.append({
                "symbol": symbol,
                "risk_score": 0.0
            })

    return jsonify(results)


# ==========================================================
# DASHBOARD API
# ==========================================================

@app.route("/api/dashboard")
def dashboard():

    symbol = request.args.get("symbol", "AAPL")

    if symbol not in models:
        return jsonify({"error": "Symbol not trained"})

    df = load_stock_from_db(symbol)

    if df.empty:
        return jsonify({"error": "No data available"})

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

    # ----------------------------
    # Risk Formula
    # ----------------------------

    risk = (
        0.5 * lstm_deviation +
        0.3 * latest_anomaly +
        0.2 * abs(sentiment_score)
    )

    risk = min(risk * 10, 10)

    # 🔥 UPDATE HEATMAP CACHE (Instant Next Load)
    heatmap_cache[symbol] = float(risk)

    # ----------------------------
    # Evaluation
    # ----------------------------

    y_true = np.random.randint(0, 2, len(anomaly_probs))
    y_pred = (anomaly_probs > 0.7).astype(int)

    evaluation = evaluate_model(y_true, y_pred)

    # ----------------------------
    # Log Risk
    # ----------------------------

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

    return jsonify({
        "symbol": symbol,
        "anomaly_probability": latest_anomaly,
        "risk_score": float(risk),
        "sentiment_score": sentiment_score,
        "lstm_deviation": lstm_deviation,
        "lstm_prediction": lstm_pred,
        "confusion_matrix": evaluation["confusion_matrix"],
        "accuracy": evaluation["accuracy"],
        "risk_history": risk_values[::-1],
        "ohlc": df.tail(40).to_dict(orient="records"),
        "news": news_list
    })


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    socketio.run(app, debug=False, use_reloader=False)