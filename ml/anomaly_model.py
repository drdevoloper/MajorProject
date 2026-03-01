import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

MODEL_DIR = "models/anomaly"
os.makedirs(MODEL_DIR, exist_ok=True)


def train_anomaly(X, symbol):

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42
    )

    model.fit(X)

    joblib.dump(model, f"{MODEL_DIR}/{symbol}.pkl")

    return model


def load_anomaly(symbol):

    return joblib.load(f"{MODEL_DIR}/{symbol}.pkl")


def anomaly_probability(model, X):

    # decision_function → higher = normal
    scores = model.decision_function(X)

    # Convert to probability-like scale (0–1)
    probs = (scores - scores.min()) / (scores.max() - scores.min())

    return 1 - probs   # higher = more anomalous