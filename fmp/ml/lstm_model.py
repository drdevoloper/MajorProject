import torch
import torch.nn as nn
import numpy as np
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

MODEL_DIR = "models/lstm"
os.makedirs(MODEL_DIR, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("LSTM using device:", device)


# =====================================================
# LSTM MODEL
# =====================================================

class LSTMModel(nn.Module):

    def __init__(self, hidden_size=64, num_layers=2):

        super().__init__()

        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )

        self.dropout = nn.Dropout(0.2)

        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):

        out, _ = self.lstm(x)

        out = self.dropout(out[:, -1, :])

        out = self.fc(out)

        return out


# =====================================================
# CREATE SEQUENCES
# =====================================================

def create_sequences(data, seq_len=20):

    X, y = [], []

    for i in range(len(data) - seq_len):

        X.append(data[i:i + seq_len])
        y.append(data[i + seq_len])

    return np.array(X), np.array(y)


# =====================================================
# TRAIN LSTM
# =====================================================

def train_lstm(df, symbol, epochs=80, seq_len=20):

    print(f"🔄 Training LSTM for {symbol}")

    close_prices = df["Close"].values.reshape(-1, 1)

    scaler = MinMaxScaler()

    scaled = scaler.fit_transform(close_prices)

    joblib.dump(scaler, f"{MODEL_DIR}/{symbol}_scaler.pkl")

    X, y = create_sequences(scaled, seq_len)

    # Train Test Split (Time Series Safe)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        shuffle=False
    )

    # Convert to tensors
    X_train = torch.tensor(X_train, dtype=torch.float32).to(device)
    y_train = torch.tensor(y_train, dtype=torch.float32).to(device)

    X_test = torch.tensor(X_test, dtype=torch.float32).to(device)
    y_test = torch.tensor(y_test, dtype=torch.float32).to(device)

    model = LSTMModel().to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    criterion = nn.MSELoss()

    for epoch in range(epochs):

        # =====================
        # TRAINING
        # =====================

        model.train()

        optimizer.zero_grad()

        output = model(X_train)

        train_loss = criterion(output.squeeze(), y_train.squeeze())

        train_loss.backward()

        optimizer.step()

        # =====================
        # TEST EVALUATION
        # =====================

        model.eval()

        with torch.no_grad():

            test_output = model(X_test)

            test_loss = criterion(
                test_output.squeeze(),
                y_test.squeeze()
            )

        if (epoch + 1) % 5 == 0:

            print(
                f"Epoch {epoch+1} | "
                f"Train Loss: {train_loss.item():.6f} | "
                f"Test Loss: {test_loss.item():.6f}"
            )

    torch.save(model.state_dict(), f"{MODEL_DIR}/{symbol}.pt")

    print("✅ LSTM training completed")

    return model


# =====================================================
# LOAD MODEL
# =====================================================

def load_lstm(symbol):

    model = LSTMModel().to(device)

    model.load_state_dict(
        torch.load(
            f"{MODEL_DIR}/{symbol}.pt",
            map_location=device
        )
    )

    model.eval()

    return model


# =====================================================
# PREDICT SERIES (FOR METRICS / GRAPH)
# =====================================================

def predict_lstm_series(model, df, symbol, seq_len=20):

    scaler = joblib.load(f"{MODEL_DIR}/{symbol}_scaler.pkl")

    close_prices = df["Close"].values.reshape(-1, 1)

    scaled = scaler.transform(close_prices)

    preds = []
    actual = []

    for i in range(seq_len, len(scaled)):

        seq = scaled[i-seq_len:i]

        X = torch.tensor([seq], dtype=torch.float32).to(device)

        with torch.no_grad():

            pred_scaled = model(X).cpu().numpy()[0][0]

        pred = scaler.inverse_transform([[pred_scaled]])[0][0]

        preds.append(pred)

        actual.append(close_prices[i][0])

    return np.array(actual), np.array(preds)


# =====================================================
# PREDICT NEXT VALUE (FOR DASHBOARD)
# =====================================================

def predict_lstm(model, df, symbol, seq_len=20):

    scaler = joblib.load(f"{MODEL_DIR}/{symbol}_scaler.pkl")

    close_prices = df["Close"].values.reshape(-1, 1)

    scaled = scaler.transform(close_prices)

    seq = scaled[-seq_len:]

    X = torch.tensor([seq], dtype=torch.float32).to(device)

    with torch.no_grad():

        pred_scaled = model(X).cpu().numpy()[0][0]

    pred = scaler.inverse_transform([[pred_scaled]])[0][0]

    return float(pred)