# File: api/equipment_endpoints.py - Final version with smart algorithm
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Import your database components
from api.database import get_db
from api.database_models import EquipmentCatalog, CargoItemTemplate, SavedOptimization

# Import both algorithms
from algorithms.advanced_packing import advanced_3d_packing
from algorithms.optimized_packing import volume_optimized_3d_packing

# Import all the models we need
from api.models import (
    # Bin packing models
    BinPackingRequest, BinPackingResponse, BinPackingItem, PlacedItem,
    Container, Container3D, CargoItem3D, PlacedItem3D, PackingRequest, PackingResponse,
    # Equipment models
    EquipmentBase, EquipmentCreate, EquipmentResponse,
    CargoTemplateBase, CargoTemplateResponse,
    SavedLayoutCreate, SavedLayoutResponse
)

# Thread pool for CPU-intensive operations
thread_pool = ThreadPoolExecutor(max_workers=4)

# Security
security = HTTPBearer()
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    expected_key = os.environ.get("API_KEY", "your-fallback-secret-key")
    if credentials.credentials != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

router = APIRouter(prefix="/api/equipment", tags=["equipment"])

# ==================== SMART ALGORITHM SELECTION ====================

def select_optimal_algorithm(total_items: int, volume_ratio: float) -> str:
    """
    Select the best algorithm based on problem characteristics
    """
    # Use optimized algorithm for:
    # 1. Large item counts (more opportunity for optimization)
    # 2. High volume ratios (need better space utilization)
    # 3. Medium complexity scenarios
    
    if total_items > 30 or volume_ratio > 0.7:
        return "volume_optimized"
    elif total_items > 10 and volume_ratio > 0.4:
        return "volume_optimized"
    else:
        return "standard"

def calculate_volume_ratio(container: Container3D, items: List[CargoItem3D]) -> float:
    """Calculate volume ratio of items to container"""
    container_volume = container.length * container.width * container.height
    total_item_volume = sum(
        item.length * item.width * item.height * item.quantity 
        for item in items
    )
    return total_item_volume / container_volume if container_volume > 0 else 0

# ==================== MAIN PACKING ENDPOINTS ====================

@router.post("/3d-bin-packing", response_model=BinPackingResponse)
async def calculate_3d_bin_packing(request: BinPackingRequest):
    """
    Main 3D bin packing endpoint with automatic algorithm selection
    """
    try:
        start_time = time.time()
        
        # Convert to Container3D format
        container = Container3D(
            length=request.container.length,
            width=request.container.width,
            height=request.container.height,
            max_weight=request.container.max_weight or 50000
        )
        
        # Convert BinPackingItem to CargoItem3D
        cargo_items = []
        total_items = sum(item.quantity for item in request.items)
        
        for item in request.items:
            cargo_items.append(CargoItem3D(
                id=item.id,
                name=item.name,
                length=item.length,
                width=item.width,
                height=item.height,
                weight=item.weight,
                quantity=item.quantity,
                non_stackable=item.non_stackable or False,
                non_rotatable=item.non_rotatable or False
            ))
        
        # Smart algorithm selection
        volume_ratio = calculate_volume_ratio(container, cargo_items)
        algorithm_choice = select_optimal_algorithm(total_items, volume_ratio)
        
        print(f"Smart selection: {algorithm_choice} (items: {total_items}, volume_ratio: {volume_ratio:.3f})")
        
        # Run selected algorithm
        loop = asyncio.get_event_loop()
        
        if algorithm_choice == "volume_optimized":
            packed_items_3d = await loop.run_in_executor(
                thread_pool,
                volume_optimized_3d_packing,
                container,
                cargo_items
            )
        else:
            packed_items_3d = await loop.run_in_executor(
                thread_pool,
                advanced_3d_packing,
                container,
                cargo_items
            )
        
        # Convert back to PlacedItem format
        placed_items = []
        for item in packed_items_3d:
            placed_items.append(PlacedItem(
                id=item.id,
                name=item.name,
                length=item.length,
                width=item.width,
                height=item.height,
                weight=item.weight,
                x=item.x,
                y=item.y,
                z=item.z,
                fitted=item.fitted,
                non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable
            ))
        
        # Calculate statistics
        fitted_items = [item for item in placed_items if item.fitted]
        total_weight = sum(item.weight for item in placed_items)
        fitted_weight = sum(item.weight for item in fitted_items)
        
        container_volume = container.length * container.width * container.height
        used_volume = sum(item.length * item.width * item.height for item in fitted_items)
        efficiency = (used_volume / container_volume * 100) if container_volume > 0 else 0
        
        processing_time = time.time() - start_time
        
        print(f"Completed in {processing_time:.2f}s using {algorithm_choice} algorithm")
        print(f"Results: {len(fitted_items)}/{len(placed_items)} items fitted ({efficiency:.1f}% efficiency)")
        
        return BinPackingResponse(
            placed_items=placed_items,
            total_items=len(placed_items),
            fitted_items=len(fitted_items),
            efficiency=round(efficiency, 2),
            total_weight=round(total_weight, 2),
            fitted_weight=round(fitted_weight, 2),
            processing_time=round(processing_time, 2)
        )
        
    except Exception as e:
        print(f"Error in main packing endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Packing calculation failed: {str(e)}")

@router.post("/3d-bin-packing-force-optimized", response_model=BinPackingResponse)
async def calculate_3d_bin_packing_force_optimized(request: BinPackingRequest):
    """
    Force use of optimized algorithm (for testing)
    """
    try:
        start_time = time.time()
        
        container = Container3D(
            length=request.container.length,
            width=request.container.width,
            height=request.container.height,
            max_weight=request.container.max_weight or 50000
        )
        
        cargo_items = []
        for item in request.items:
            cargo_items.append(CargoItem3D(
                id=item.id, name=item.name,
                length=item.length, width=item.width, height=item.height,
                weight=item.weight, quantity=item.quantity,
                non_stackable=item.non_stackable or False,
                non_rotatable=item.non_rotatable or False
            ))
        
        # Force optimized algorithm
        loop = asyncio.get_event_loop()
        packed_items_3d = await loop.run_in_executor(
            thread_pool,
            volume_optimized_3d_packing,
            container,
            cargo_items
        )
        
        # Convert back to PlacedItem format
        placed_items = []
        for item in packed_items_3d:
            placed_items.append(PlacedItem(
                id=item.id, name=item.name,
                length=item.length, width=item.width, height=item.height,
                weight=item.weight, x=item.x, y=item.y, z=item.z,
                fitted=item.fitted, non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable
            ))
        
        # Calculate statistics
        fitted_items = [item for item in placed_items if item.fitted]
        total_weight = sum(item.weight for item in placed_items)
        fitted_weight = sum(item.weight for item in fitted_items)
        
        container_volume = container.length * container.width * container.height
        used_volume = sum(item.length * item.width * item.height for item in fitted_items)
        efficiency = (used_volume / container_volume * 100) if container_volume > 0 else 0
        
        processing_time = time.time() - start_time
        
        return BinPackingResponse(
            placed_items=placed_items,
            total_items=len(placed_items),
            fitted_items=len(fitted_items),
            efficiency=round(efficiency, 2),
            total_weight=round(total_weight, 2),
            fitted_weight=round(fitted_weight, 2),
            processing_time=round(processing_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forced optimized packing failed: {str(e)}")

@router.post("/3d-bin-packing-force-basic", response_model=BinPackingResponse)
async def calculate_3d_bin_packing_force_basic(request: BinPackingRequest):
    """
    Force use of basic algorithm (for comparison)
    """
    try:
        container = Container3D(
            length=request.container.length,
            width=request.container.width,
            height=request.container.height,
            max_weight=request.container.max_weight or 50000
        )
        
        cargo_items = []
        for item in request.items:
            cargo_items.append(CargoItem3D(
                id=item.id, name=item.name,
                length=item.length, width=item.width, height=item.height,
                weight=item.weight, quantity=item.quantity,
                non_stackable=item.non_stackable or False,
                non_rotatable=item.non_rotatable or False
            ))
        
        # Force basic algorithm
        loop = asyncio.get_event_loop()
        packed_items_3d = await loop.run_in_executor(
            thread_pool,
            advanced_3d_packing,
            container,
            cargo_items
        )
        
        # Convert and return (same as above)
        placed_items = []
        for item in packed_items_3d:
            placed_items.append(PlacedItem(
                id=item.id, name=item.name,
                length=item.length, width=item.width, height=item.height,
                weight=item.weight, x=item.x, y=item.y, z=item.z,
                fitted=item.fitted, non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable
            ))
        
        fitted_items = [item for item in placed_items if item.fitted]
        total_weight = sum(item.weight for item in placed_items)
        fitted_weight = sum(item.weight for item in fitted_items)
        
        container_volume = container.length * container.width * container.height
        used_volume = sum(item.length * item.width * item.height for item in fitted_items)
        efficiency = (used_volume / container_volume * 100) if container_volume > 0 else 0
        
        return BinPackingResponse(
            placed_items=placed_items,
            total_items=len(placed_items),
            fitted_items=len(fitted_items),
            efficiency=round(efficiency, 2),
            total_weight=round(total_weight, 2),
            fitted_weight=round(fitted_weight, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forced basic packing failed: {str(e)}")

# ==================== DEBUG AND TEST ENDPOINTS ====================

@router.post("/test-basic-packing")
async def test_basic_packing(request: BinPackingRequest):
    """
    Super simple test - just place first item at origin
    """
    placed_items = []
    for i, item in enumerate(request.items):
        if i == 0:  # Only first item
            placed_items.append(PlacedItem(
                id=item.id, name=item.name,
                length=item.length, width=item.width, height=item.height,
                weight=item.weight, x=0, y=0, z=0, fitted=True,
                non_stackable=item.non_stackable, non_rotatable=item.non_rotatable
            ))
        else:
            placed_items.append(PlacedItem(
                id=item.id, name=item.name,
                length=item.length, width=item.width, height=item.height,
                weight=item.weight, x=0, y=0, z=0, fitted=False,
                non_stackable=item.non_stackable, non_rotatable=item.non_rotatable
            ))
    
    return BinPackingResponse(
        placed_items=placed_items,
        total_items=len(placed_items),
        fitted_items=1,
        efficiency=10.0,
        total_weight=100.0,
        fitted_weight=10.0
    )

# ==================== LEGACY ENDPOINTS ====================

@router.post("/3d-packing", response_model=PackingResponse)
async def optimize_3d_packing(request: PackingRequest):
    """Legacy 3D packing endpoint for backward compatibility"""
    try:
        packed_items = await asyncio.get_event_loop().run_in_executor(
            thread_pool, advanced_3d_packing, request.container, request.items
        )
        
        fitted_items = [item for item in packed_items if item.fitted]
        total_volume = request.container.length * request.container.width * request.container.height
        used_volume = sum(item.length * item.width * item.height for item in fitted_items)
        
        stats = {
            "total_items": len(packed_items),
            "fitted_items": len(fitted_items),
            "unfitted_items": len(packed_items) - len(fitted_items),
            "space_efficiency": round((used_volume / total_volume * 100) if total_volume > 0 else 0, 2),
            "total_weight": round(sum(item.weight for item in packed_items), 2),
            "fitted_weight": round(sum(item.weight for item in fitted_items), 2)
        }
        
        return PackingResponse(placed_items=packed_items, stats=stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Packing calculation failed: {str(e)}")

# [All your existing equipment/cargo/layout endpoints remain the same]
# ==================== EQUIPMENT ENDPOINTS ====================

@router.get("/containers", response_model=List[EquipmentResponse])
async def get_all_equipment(
    category: Optional[str] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Show only active equipment"),
    db: Session = Depends(get_db)
):
    """Get all equipment/containers with optional filtering"""
    query = db.query(EquipmentCatalog)
    
    if category:
        query = query.filter(EquipmentCatalog.category == category)
    
    if active_only:
        query = query.filter(EquipmentCatalog.is_active == True)
    
    equipment = query.order_by(EquipmentCatalog.category, EquipmentCatalog.name).all()
    return [EquipmentResponse.model_validate(eq) for eq in equipment]

# Legacy compatibility endpoint
@router.get("/presets")
async def get_legacy_presets(db: Session = Depends(get_db)):
    """Legacy endpoint for backward compatibility with frontend"""
    equipment = db.query(EquipmentCatalog).filter(
        EquipmentCatalog.is_preset == True, 
        EquipmentCatalog.is_active == True
    ).all()
    
    # Convert to old format
    presets = {}
    for eq in equipment:
        # Convert cm back to original units
        if eq.original_unit == "in":
            length = eq.length_cm / 2.54
            width = eq.width_cm / 2.54
            height = eq.height_cm / 2.54
        else:
            length = eq.length_cm
            width = eq.width_cm  
            height = eq.height_cm
        
        presets[eq.type_code] = {
            "length": length,
            "width": width,
            "height": height,
            "name": eq.name,
            "units": eq.original_unit
        }
    
    return presets