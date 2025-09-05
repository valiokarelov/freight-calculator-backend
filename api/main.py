from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os

# Import your calculations router
from api.calculations import router as calculations_router
# Add this line to import the equipment router
from api.equipment_endpoints import router as equipment_router

app = FastAPI(title="Freight Calculator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the calculations router
app.include_router(calculations_router, prefix="/api/calculations")
# Add this line to include the equipment router
app.include_router(equipment_router)

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
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)