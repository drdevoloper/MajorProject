from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
from threading import Thread
import time
import datetime
import numpy as np
from preprocess.stock_data import fetch_and_store_stock, load_stock_from_db
from preprocess.feature_engineering import create_features, fit_scaler
from preprocess.news_data import get_news, store_news

from ml.anomaly_model import train_anomaly, anomaly_probability
from ml.lstm_model import train_lstm, load_lstm, predict_lstm, predict_lstm_series
from ml.bert_model import FinBERT

from ml.risk_engine import train_risk_model, load_risk_model, calculate_risk
from ml.evaluation import evaluate_models

from config import SYMBOLS
from database.mongo import logs, db

import torch

torch.backends.cudnn.benchmark = True


# ==================================================
# APP INIT
# ==================================================

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

bert = FinBERT()

models = {}
scalers = {}
lstm_models = {}

dashboard_cache = {}
heatmap_cache = {}

risk_model = None


# ==================================================
# INITIAL DATA FETCH
# ==================================================

def initialize_data():

    print("📥 Fetching stock data and news...")

    for symbol in SYMBOLS:

        try:
            fetch_and_store_stock(symbol)
            store_news(symbol)

        except Exception as e:
            print("❌ Data fetch error:", symbol, e)

    print("✅ Stock data and news ready")


# ==================================================
# TRAIN BASE MODELS
# ==================================================

def train_all():

    print("🔄 Training base models...")

    lstm_true = []
    lstm_pred = []

    anomaly_true = []
    anomaly_pred = []

    sentiment_true = []
    sentiment_pred = []

    for symbol in SYMBOLS:

        df = load_stock_from_db(symbol)

        if df.empty:
            continue

        X = create_features(df, symbol=symbol, store=True)

        scaler = fit_scaler(X.values, symbol)

        scalers[symbol] = scaler

        X_scaled = scaler.transform(X.values)

        models[symbol] = train_anomaly(X_scaled, symbol)

        anomaly_probs = anomaly_probability(models[symbol], X_scaled)

        pred_labels = (anomaly_probs > 0.7).astype(int)

        threshold = np.percentile(anomaly_probs, 95)

        true_labels = (anomaly_probs > threshold).astype(int)

        anomaly_true.extend(true_labels.tolist())
        anomaly_pred.extend(pred_labels.tolist())

        train_lstm(df, symbol)

        lstm_models[symbol] = load_lstm(symbol)

        actual, predicted = predict_lstm_series(
            lstm_models[symbol], df, symbol
        )

        for a, p in zip(actual[-200:], predicted[-200:]):

            if not np.isnan(a) and not np.isnan(p):

                lstm_true.append(float(a))
                lstm_pred.append(float(p))

        news = get_news(symbol, 50)

        if news and len(df) > 1:

            titles = [n["title"] for n in news]

            probs = bert.sentiment(titles)

            price_change = df["Close"].pct_change().iloc[-1]

            if price_change > 0.01:
                price_label = 2
            elif price_change < -0.01:
                price_label = 0
            else:
                price_label = 1

            for prob in probs:

                pred_label = int(np.argmax(prob))

                sentiment_true.append(price_label)
                sentiment_pred.append(pred_label)

    print("✅ Base models trained")

    evaluate_models(

        np.array(lstm_true),
        np.array(lstm_pred),

        np.array(anomaly_true),
        np.array(anomaly_pred),

        np.array(sentiment_true),
        np.array(sentiment_pred)
    )


# ==================================================
# RISK ENGINE
# ==================================================

def compute_symbol(symbol):

    if symbol not in scalers:
        return None

    df = load_stock_from_db(symbol)

    if df.empty:
        return None

    X = create_features(df, symbol=symbol, store=False)

    X_scaled = scalers[symbol].transform(X.values)

    anomaly_probs = anomaly_probability(models[symbol], X_scaled)

    latest_anomaly = float(anomaly_probs[-1])

    current_price = df["Close"].iloc[-1]

    lstm_pred = predict_lstm(lstm_models[symbol], df, symbol)

    lstm_deviation = abs(current_price - lstm_pred) / (current_price + 1e-6)
    lstm_deviation = min(lstm_deviation, 1)

    # ==================================================
    # NEWS + SENTIMENT
    # ==================================================

    news = get_news(symbol, 50)

    sentiment_score = 0.5
    news_list = []

    positive = 0
    neutral = 0
    negative = 0

    if news:

        titles = [n["title"] for n in news[:20]]

        probs = bert.sentiment(titles)

        scores = []

        for title, prob in zip(titles, probs):

            pos = float(prob[2])
            neu = float(prob[1])
            neg = float(prob[0])

            scores.append(pos)

            if pos > neu and pos > neg:
                positive += 1
            elif neg > pos and neg > neu:
                negative += 1
            else:
                neutral += 1

            news_list.append({
                "title": title,
                "sentiment": pos
            })

        sentiment_score = float(np.mean(scores))

    # ==================================================
    # SENTIMENT DISTRIBUTION
    # ==================================================

    total = positive + neutral + negative

    if total == 0:
        total = 1

    sentiment_distribution = {
        "positive": round((positive / total) * 100, 2),
        "neutral": round((neutral / total) * 100, 2),
        "negative": round((negative / total) * 100, 2)
    }

    # ==================================================
    # VOLATILITY
    # ==================================================

    returns = df["Close"].pct_change().dropna()

    volatility = float(returns.std() * np.sqrt(252) * 100)

    volatility_norm = min(volatility / 100, 1)

    # ==================================================
    # STORE TRAINING DATA
    # ==================================================

    risk_rule = (
        0.35 * latest_anomaly +
        0.30 * lstm_deviation +
        0.20 * volatility_norm +
        0.15 * (1 - sentiment_score)
    )

    risk_label = 1 if risk_rule > 0.55 else 0

    db.risk_training_data.insert_one({

        "symbol": symbol,
        "anomaly": latest_anomaly,
        "sentiment": sentiment_score,
        "volatility": volatility_norm,
        "lstm_dev": lstm_deviation,
        "risk_label": risk_label,
        "timestamp": datetime.datetime.utcnow()

    })

    # ==================================================
    # RISK SCORE
    # ==================================================

    if risk_model:

        risk_prob = calculate_risk(
            risk_model,
            latest_anomaly,
            sentiment_score,
            volatility_norm,
            lstm_deviation
        )

    else:

        risk_prob = risk_rule

    risk = min(risk_prob * 10, 10)

    logs.insert_one({

        "symbol": symbol,
        "risk": float(risk),
        "timestamp": datetime.datetime.utcnow()

    })


    # ==================================================
    # Feature Importance Risk Drivers
    # ==================================================

    risk_drivers = {}

    try:
        if risk_model:

            importances = risk_model.feature_importances_

            feature_names = [
                "Anomaly",
                "Sentiment",
                "Volatility",
                "LSTM Dev"
            ]

            total = np.sum(importances)

            if total == 0:
                total = 1

            for name, val in zip(feature_names, importances):
                risk_drivers[name] = round((val / total) * 100, 2)

    except Exception as e:
        print("Risk driver error:", e)

    # ==================================================
    # RISK HISTORY (LAST 10)
    # ==================================================

    history_cursor = logs.find(
        {"symbol": symbol}
    ).sort("timestamp", -1).limit(10)

    risk_history = [float(h["risk"]) for h in history_cursor]

    risk_history.reverse()

    # ==================================================
    # OHLC DATA
    # ==================================================

    df_tail = df.tail(40).copy()

    if "Date" in df_tail.columns:
        df_tail["Date"] = df_tail["Date"].astype(str)

    ohlc_records = df_tail.to_dict(orient="records")

    return {

        "symbol": symbol,
        "risk_score": float(risk),

        "sentiment_score": float(sentiment_score),

        "sentiment_distribution": sentiment_distribution,

        "risk_history": risk_history,

        "risk_drivers": risk_drivers,

        "lstm_deviation": float(lstm_deviation),
        "anomaly_probability": latest_anomaly,

        "volatility": volatility,

        "ohlc": ohlc_records,

        "news": news_list
    }


# ==================================================
# BACKGROUND ENGINE
# ==================================================

def background_risk_engine():

    print("🚀 Background risk engine started")

    while True:

        for symbol in SYMBOLS:

            try:

                fetch_and_store_stock(symbol)
                store_news(symbol)

                result = compute_symbol(symbol)

                if result:

                    dashboard_cache[symbol] = result
                    heatmap_cache[symbol] = result["risk_score"]

            except Exception as e:

                print("❌ Error computing", symbol, e)

        socketio.emit("heatmap_update", heatmap_cache)

        print("✅ Cache refreshed")

        time.sleep(300)


# ==================================================
# ROUTES
# ==================================================

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

    return jsonify(data)


# ==================================================
# SOCKET
# ==================================================

@socketio.on("request_dashboard")
def handle_dashboard_request(data):

    symbol = data.get("symbol") or "AAPL"

    try:

        result = compute_symbol(symbol)

        if result:

            dashboard_cache[symbol] = result
            heatmap_cache[symbol] = result["risk_score"]

            socketio.emit(
                "dashboard_update",
                result,
                to=request.sid
            )

    except Exception as e:

        print("Dashboard error:", e)


# ==================================================
# STARTUP
# ==================================================

initialize_data()
train_all()

risk_model = load_risk_model()

if risk_model is None:
    risk_model = train_risk_model()


# ==================================================
# RUN SERVER
# ==================================================

if __name__ == "__main__":

    worker = Thread(target=background_risk_engine)
    worker.daemon = True
    worker.start()

    socketio.run(app, debug=False, use_reloader=False)