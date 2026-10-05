import json
import torch
from fastapi import FastAPI

# Carrega o artefato do volume compartilhado com o container de treino
model = torch.jit.load("/models/model.pt")
model.eval()
meta = json.load(open("/models/metadata.json"))

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict():
    # Usa os últimos fechamentos salvos no treino
    closes = meta["last_closes"]

    # Mesma normalização do treino: preço/último - 1
    last = closes[-1]
    x = torch.tensor([[[c / last - 1] for c in closes]])
    with torch.no_grad():
        variacao = model(x).item()

    return {"ultimo_fechamento": last, "previsao_proximo_dia": round(last * (1 + variacao), 2)}
