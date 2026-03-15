import os
import joblib
import numpy as np
import xgboost as xgb
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from database.mongo import db

MODEL_DIR = "models/risk"
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = f"{MODEL_DIR}/risk_model.pkl"


# ======================================
# LOAD DATA FROM MONGODB
# ======================================

def load_dataset():

    records = list(db.risk_training_data.find())

    if len(records) < 50:
        print("⚠ Not enough training samples")
        return None

    df = pd.DataFrame(records)

    X = df[[
        "anomaly",
        "sentiment",
        "volatility",
        "lstm_dev"
    ]].values

    y = df["risk_label"].values

    return X, y


# ======================================
# TRAIN MODEL
# ======================================

def train_risk_model():

    print("🔄 Training Risk Model From MongoDB")

    data = load_dataset()

    if data is None:
        return None

    X, y = data

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss"
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    print("\n📊 Risk Model Evaluation")
    print("Accuracy:", accuracy_score(y_test, preds))
    print("Precision:", precision_score(y_test, preds))
    print("Recall:", recall_score(y_test, preds))
    print("F1:", f1_score(y_test, preds))

    joblib.dump(model, MODEL_PATH)

    print("✅ Risk model saved")

    return model


# ======================================
# LOAD MODEL
# ======================================

def load_risk_model():

    if not os.path.exists(MODEL_PATH):

        print("⚠ No risk model found")

        return train_risk_model()

    print("✅ Risk model loaded")

    return joblib.load(MODEL_PATH)


# ======================================
# CALCULATE RISK
# ======================================

def calculate_risk(model, anomaly, sentiment, volatility, lstm_dev):

    features = np.array([
        anomaly,
        sentiment,
        volatility,
        lstm_dev
    ]).reshape(1,-1)

    prob = model.predict_proba(features)[0][1]

    return float(prob)