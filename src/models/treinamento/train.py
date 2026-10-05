import json
import numpy as np
import pandas as pd
import torch
from torch import nn

WINDOW = 30      
HIDDEN = 32
EPOCHS = 100
LR = 1e-3
torch.manual_seed(42)

df = pd.read_csv("/data/btc_usd_3y.csv", parse_dates=["Date"]).sort_values("Date")
close = df["Close"].astype(float).values


# Cada janela é normalizada pelo seu último fechamento: entrada = preço/último - 1,
def make_windows(series):
    X, y = [], []
    for i in range(len(series) - WINDOW):
        win, last = series[i:i + WINDOW], series[i + WINDOW - 1]
        X.append(win / last - 1)
        y.append(series[i + WINDOW] / last - 1)
    return np.array(X, dtype=np.float32)[..., None], np.array(y, dtype=np.float32)


X, y = make_windows(close)

# Split cronológico (sem embaralhar)
cut = int(len(X) * 0.8)
X_tr, X_te, y_tr, y_te = map(torch.from_numpy, (X[:cut], X[cut:], y[:cut], y[cut:]))


class LSTMRegressor(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1]).squeeze(-1)


model = LSTMRegressor(HIDDEN)
opt = torch.optim.Adam(model.parameters(), lr=LR)
loss_fn = nn.MSELoss()

for epoch in range(1, EPOCHS + 1):
    model.train()
    opt.zero_grad()
    loss = loss_fn(model(X_tr), y_tr)
    loss.backward()
    opt.step()
    if epoch % 10 == 0:
        print(f"época {epoch:3d} | loss treino {loss.item():.6f}")

# Avaliação em dólares: converte a variação prevista de volta para preço
model.eval()
with torch.no_grad():
    pred_ret = model(X_te).numpy()
last_te = close[cut + WINDOW - 1:-1]
true_te = close[cut + WINDOW:]
mae = float(np.mean(np.abs(last_te * (1 + pred_ret) - true_te)))
baseline = float(np.mean(np.abs(last_te - true_te)))  # "amanhã = hoje"
print(f"MAE modelo: {mae:.2f} | MAE baseline: {baseline:.2f}")

# TorchScript: o container de inferência carrega com torch.jit
torch.jit.script(model).save("/models/model.pt")
json.dump({"window": WINDOW, "mae": mae, "baseline_mae": baseline,
           "last_date": str(df["Date"].iloc[-1].date()),
           "last_closes": close[-WINDOW:].tolist()},
          open("/models/metadata.json", "w"))
print("Modelo salvo em /models/model.pt")
