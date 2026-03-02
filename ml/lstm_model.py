import torch
import torch.nn as nn
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler

MODEL_DIR = "models/lstm"
os.makedirs(MODEL_DIR, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("LSTM using device:", device)


class LSTMModel(nn.Module):

    def __init__(self, hidden_size=64, num_layers=2):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=1,      # ONLY CLOSE PRICE
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


# -----------------------------------------------------
# Create Sequences
# -----------------------------------------------------
def create_sequences(data, seq_len=20):

    X, y = [], []

    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len])
        y.append(data[i+seq_len])

    return np.array(X), np.array(y)


# -----------------------------------------------------
# TRAIN
# -----------------------------------------------------
def train_lstm(df, symbol, epochs=30, seq_len=20):

    print(f"🔄 Training LSTM for {symbol}")

    close_prices = df["Close"].values.reshape(-1, 1)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(close_prices)

    # Save scaler
    np.save(f"{MODEL_DIR}/{symbol}_scaler.npy", scaler.scale_)
    np.save(f"{MODEL_DIR}/{symbol}_min.npy", scaler.min_)

    X, y = create_sequences(scaled, seq_len)

    X = torch.tensor(X, dtype=torch.float32).to(device)
    y = torch.tensor(y, dtype=torch.float32).to(device)

    model = LSTMModel().to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    for epoch in range(epochs):

        model.train()
        optimizer.zero_grad()

        output = model(X)
        loss = criterion(output.squeeze(), y.squeeze())

        loss.backward()
        optimizer.step()

        if (epoch+1) % 5 == 0:
            print(f"Epoch {epoch+1} | Loss: {loss.item():.6f}")

    torch.save(model.state_dict(), f"{MODEL_DIR}/{symbol}.pt")

    print("✅ LSTM training completed")


# -----------------------------------------------------
# LOAD
# -----------------------------------------------------
def load_lstm(symbol):

    path = f"{MODEL_DIR}/{symbol}.pt"

    model = LSTMModel().to(device)

    model.load_state_dict(
        torch.load(path, map_location=device)
    )

    model.eval()

    return model


# -----------------------------------------------------
# PREDICT
# -----------------------------------------------------
def predict_lstm(model, df, symbol, seq_len=20):

    close_prices = df["Close"].values.reshape(-1, 1)

    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(close_prices)

    last_seq = scaled[-seq_len:]

    X = torch.tensor([last_seq], dtype=torch.float32).to(device)

    with torch.no_grad():
        with torch.cuda.amp.autocast():
            pred_scaled = model(X)

    pred_scaled = pred_scaled.cpu().numpy()[0][0]

    pred_actual = scaler.inverse_transform(
        [[pred_scaled]]
    )[0][0]

    return float(pred_actual)