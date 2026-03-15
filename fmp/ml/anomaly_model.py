import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

MODEL_DIR = os.path.join("models", "anomaly")
os.makedirs(MODEL_DIR, exist_ok=True)


def train_anomaly(X, symbol):
    """
    Train Isolation Forest model for anomaly detection
    """

    # Train-test split (time-series safe)
    X_train, X_test = train_test_split(
        X,
        test_size=0.2,
        shuffle=False,
        random_state=42
    )

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42
    )

    # Train model
    model.fit(X_train)

    # Evaluate model
    test_scores = model.decision_function(X_test)
    preds = model.predict(X_test)

    # Convert (-1 anomaly → 1, normal → 0)
    preds = np.where(preds == -1, 1, 0)

    # Save model
    model_path = os.path.join(MODEL_DIR, f"{symbol}.pkl")
    joblib.dump(model, model_path)

    return model


def load_anomaly(symbol):
    """
    Load saved anomaly model
    """

    model_path = os.path.join(MODEL_DIR, f"{symbol}.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model for {symbol} not found. Train the model first.")

    return joblib.load(model_path)


def anomaly_probability(model, X):
    """
    Convert Isolation Forest scores to anomaly probability
    """

    scores = model.decision_function(X)

    min_score = scores.min()
    max_score = scores.max()

    # Prevent division by zero
    if max_score - min_score == 0:
        return np.zeros(len(scores))

    # Normalize scores (0-1)
    probs = (scores - min_score) / (max_score - min_score)

    # Higher value → higher anomaly
    return 1 - probs