# Crypto transaction scoring service (Isolation Forest)
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

FEATURES = ["tx_amount_usd", "gas_fee_usd", "tx_velocity_1h"]
model = joblib.load(Path(__file__).parent / "isolation_forest.joblib")

app = FastAPI(title="Crypto Transaction Scoring API", version="1.0.0")


class Transaction(BaseModel):
    tx_amount_usd: float = Field(..., ge=0, examples=[12500.50])
    gas_fee_usd: float = Field(..., ge=0, examples=[45.20])
    tx_velocity_1h: int = Field(..., ge=0, examples=[4])


class Verdict(BaseModel):
    anomaly_score: float  # higher = more anomalous
    anomaly_detected: bool
    routing_action: str   # APPROVE or MANUAL_REVIEW


@app.get("/health")
def health():
    return {"status": "ok"}


# Plain `def`: FastAPI runs it in a worker thread, so CPU-bound scoring does not block the event loop
@app.post("/api/v1/score", response_model=Verdict)
def score(tx: Transaction) -> Verdict:
    X = pd.DataFrame([tx.model_dump()])[FEATURES]
    raw = float(model.score_samples(X)[0])
    flagged = raw < model.offset_  # same rule as model.predict(X) == -1
    return Verdict(anomaly_score=-raw,
                   anomaly_detected=bool(flagged),
                   routing_action="MANUAL_REVIEW" if flagged else "APPROVE")
