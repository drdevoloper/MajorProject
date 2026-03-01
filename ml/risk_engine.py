import os
import joblib
import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score

MODEL_DIR = "models/risk"
os.makedirs(MODEL_DIR, exist_ok=True)


# ======================================
# 1️⃣ TRAIN XGBOOST RISK MODEL
# ======================================

def train_risk_model(X, y):

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        use_label_encoder=False
    )

    model.fit(X, y)

    joblib.dump(model, f"{MODEL_DIR}/risk_model.pkl")

    return model


# ======================================
# 2️⃣ LOAD MODEL
# ======================================

def load_risk_model():

    return joblib.load(f"{MODEL_DIR}/risk_model.pkl")


# ======================================
# 3️⃣ CALCULATE RISK PROBABILITY
# ======================================

def calculate_risk(model, anomaly, sentiment, deviation, lstm_dev=None):

    features = [anomaly, sentiment, deviation]

    if lstm_dev is not None:
        features.append(lstm_dev)

    features = np.array([features])

    prob = model.predict_proba(features)[0][1]

    return float(prob)