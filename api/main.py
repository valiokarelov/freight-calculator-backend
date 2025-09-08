from fastapi import FastAPI, HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from api.calculations import BinPackingRequest, BinPackingResponse, advanced_bin_packing, Container, BinPackingItem, PlacedItem
import os

# Import your calculations router
from api.calculations import router as calculations_router
# Add this line to import the equipment router
from api.equipment_endpoints import router as equipment_router

app = FastAPI(title="Freight Calculator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server  
        "https://cargosizer-website.netlify.app",  # Your Netlify domain
        "https://www.cargosizer.com"  # Your custom domain
    ],
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

@app.post("/api/volume-calculator")
async def volume_calculator_frontend(request: dict):
    """
    Volume calculator endpoint that matches frontend expectations exactly
    """
    try:
        # Convert frontend request to backend format
        container_data = request.get("container", {})
        cargo_data = request.get("cargo", [])
        
        # Create container object
        container = Container(
            length=container_data.get("length", 0),
            width=container_data.get("width", 0), 
            height=container_data.get("height", 0),
            max_weight=container_data.get("maxWeight", 50000)
        )
        
        # Convert cargo items
        items = []
        for i, item in enumerate(cargo_data):
            items.append(BinPackingItem(
                id=item.get("id", f"item-{i}"),
                name=item.get("name", f"Item {i+1}"),
                length=item.get("length", 0),
                width=item.get("width", 0),
                height=item.get("height", 0),
                weight=item.get("weight", 10),  # Default weight
                quantity=item.get("quantity", 1),
                non_stackable=item.get("non_stackable", False),
                non_rotatable=item.get("non_rotatable", False)
            ))
        
        # Use advanced packing algorithm
        expanded_items = []
        for item in items:
            for i in range(item.quantity):
                expanded_items.append(PlacedItem(
                    id=f"{item.id}_{i}" if item.quantity > 1 else item.id,
                    name=f"{item.name} #{i+1}" if item.quantity > 1 else item.name,
                    length=item.length,
                    width=item.width,
                    height=item.height,
                    weight=item.weight,
                    x=0, y=0, z=0,
                    fitted=False,
                    non_stackable=item.non_stackable,
                    non_rotatable=item.non_rotatable
                ))
        
        placed_items = advanced_bin_packing(container, expanded_items)
        
        # Calculate results
        fitted_items = [item for item in placed_items if item.fitted]
        unfitted_items = [item for item in placed_items if not item.fitted]
        
        # Calculate volumes
        total_volume = sum(item.length * item.width * item.height for item in placed_items) / 1000000
        fitted_volume = sum(item.length * item.width * item.height for item in fitted_items) / 1000000
        unfitted_volume = total_volume - fitted_volume
        
        # Create response matching frontend expectations
        response = {
            "totalVolume": round(total_volume, 3),
            "fittedVolume": round(fitted_volume, 3),
            "unfittedVolume": round(unfitted_volume, 3),
            "allItemsFit": len(unfitted_items) == 0,
            "spatiallyValid": len(unfitted_items) == 0,
            "issues": [f"Item {item.id} could not be placed due to spatial constraints" for item in unfitted_items],
            "itemPlacements": [
                {
                    "itemIndex": i,
                    "fitted": item.fitted,
                    "position": {"x": item.x, "y": item.y, "z": item.z} if item.fitted else None,
                    "originalDimensions": {
                        "length": item.length,
                        "width": item.width,
                        "height": item.height
                    },
                    "quantity": 1
                }
                for i, item in enumerate(placed_items)
            ],
            "loadingSequence": [
                {
                    "step": i + 1,
                    "item": item.id,
                    "position": {"x": item.x, "y": item.y, "z": item.z}
                }
                for i, item in enumerate(fitted_items)
            ]
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"3D calculation failed: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "freight-calculator-backend"}

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