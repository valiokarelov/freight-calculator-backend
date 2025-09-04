from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os

app = FastAPI(title="Freight Calculator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChargeableWeightRequest(BaseModel):
    length: float
    width: float
    height: float
    actual_weight: float
    pieces: int = 1

@app.get("/")
def read_root():
    return {"message": "Freight Calculator API is running"}

@app.post("/api/calculations/chargeable-weight")
def calculate_chargeable_weight(request: ChargeableWeightRequest):
    # Simple calculation without numpy
    volumetric_weight = (request.length * request.width * request.height * request.pieces) / 6000
    chargeable_weight = max(request.actual_weight * request.pieces, volumetric_weight)
    cbm = (request.length * request.width * request.height * request.pieces) / 1000000
    
    return {
        "actual_weight": request.actual_weight * request.pieces,
        "volumetric_weight": volumetric_weight,
        "chargeable_weight": chargeable_weight,
        "cbm": cbm
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)