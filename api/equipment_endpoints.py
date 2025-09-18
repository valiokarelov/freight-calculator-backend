# File: api/equipment_endpoints.py - Updated with volume optimization
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

# Import BOTH algorithms - original and optimized
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
# Im port debugalgorithm
from algorithms.debug_packing import debug_3d_packing

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
    if total_items > 50 or volume_ratio > 0.8:
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

# ==================== OPTIMIZED ENDPOINTS ====================

@router.post("/3d-bin-packing-smart", response_model=BinPackingResponse)
async def calculate_3d_bin_packing_smart(request: BinPackingRequest):
    """
    Smart 3D bin packing with automatic algorithm selection
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
        
        # Calculate volume ratio for algorithm selection
        volume_ratio = calculate_volume_ratio(container, cargo_items)
        algorithm_choice = select_optimal_algorithm(total_items, volume_ratio)
        
        print(f"Algorithm selection: {algorithm_choice} (items: {total_items}, volume_ratio: {volume_ratio:.2f})")
        
        # Run appropriate algorithm in thread pool
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
        
        # Calculate volume efficiency
        container_volume = container.length * container.width * container.height
        used_volume = sum(item.length * item.width * item.height for item in fitted_items)
        efficiency = (used_volume / container_volume * 100) if container_volume > 0 else 0
        
        processing_time = time.time() - start_time
        
        print(f"Completed in {processing_time:.2f}s using {algorithm_choice} algorithm")
        
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
        raise HTTPException(status_code=500, detail=f"Packing calculation failed: {str(e)}")

@router.post("/3d-bin-packing-volume-optimized", response_model=BinPackingResponse)
async def calculate_3d_bin_packing_volume_optimized(request: BinPackingRequest):
    """
    Volume-optimized 3D bin packing for large item sets
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
        
        # Run volume-optimized packing in thread pool
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
        
        # Calculate volume efficiency
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
        raise HTTPException(status_code=500, detail=f"Volume-optimized packing failed: {str(e)}")

# ==================== BATCH PROCESSING FOR VERY LARGE SETS ====================

@router.post("/3d-bin-packing-batch-smart", response_model=BinPackingResponse)
async def calculate_3d_bin_packing_batch_smart(request: BinPackingRequest):
    """
    Intelligent batch processing for very large item sets (500+ items)
    """
    try:
        total_items = sum(item.quantity for item in request.items)
        
        if total_items > 500:
            return await process_in_smart_batches(request, batch_size=100)
        else:
            # Use smart single-pass algorithm
            return await calculate_3d_bin_packing_smart(request)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

async def process_in_smart_batches(request: BinPackingRequest, batch_size: int = 100) -> BinPackingResponse:
    """
    Smart batch processing with volume-aware item selection
    """
    # Expand all items first
    expanded_items = []
    for item in request.items:
        for i in range(item.quantity):
            expanded_items.append(BinPackingItem(
                id=f"{item.id}_{i}" if item.quantity > 1 else item.id,
                name=f"{item.name} #{i+1}" if item.quantity > 1 else item.name,
                length=item.length,
                width=item.width,
                height=item.height,
                weight=item.weight,
                quantity=1,
                non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable
            ))
    
    # Sort items by volume (largest first) for better batching
    expanded_items.sort(key=lambda x: x.length * x.width * x.height, reverse=True)
    
    all_placed_items = []
    container_volume = request.container.length * request.container.width * request.container.height
    remaining_volume = container_volume
    
    print(f"Processing {len(expanded_items)} items in smart batches of {batch_size}")
    
    # Process in batches
    for batch_num, i in enumerate(range(0, len(expanded_items), batch_size)):
        batch = expanded_items[i:i + batch_size]
        
        # Skip batch if remaining volume is insufficient
        batch_volume = sum(item.length * item.width * item.height for item in batch)
        if remaining_volume < batch_volume * 0.3:  # Need at least 30% packing efficiency
            print(f"Skipping batch {batch_num + 1}: insufficient volume")
            # Mark remaining items as not fitted
            for item in batch:
                all_placed_items.append(PlacedItem(
                    id=item.id, name=item.name,
                    length=item.length, width=item.width, height=item.height,
                    weight=item.weight, x=0, y=0, z=0, fitted=False,
                    non_stackable=item.non_stackable, non_rotatable=item.non_rotatable
                ))
            continue
        
        batch_request = BinPackingRequest(
            container=request.container,
            items=batch
        )
        
        print(f"Processing batch {batch_num + 1}/{(len(expanded_items) + batch_size - 1) // batch_size}")
        
        # Process this batch with volume-optimized algorithm
        batch_result = await calculate_3d_bin_packing_volume_optimized(batch_request)
        
        # Update remaining volume
        fitted_volume = sum(
            item.length * item.width * item.height 
            for item in batch_result.placed_items if item.fitted
        )
        remaining_volume -= fitted_volume
        
        all_placed_items.extend(batch_result.placed_items)
        
        print(f"Batch {batch_num + 1} complete: {batch_result.fitted_items}/{len(batch)} items placed")
    
    # Compile final statistics
    fitted_items = [item for item in all_placed_items if item.fitted]
    total_weight = sum(item.weight for item in all_placed_items)
    fitted_weight = sum(item.weight for item in fitted_items)
    
    container_volume = request.container.length * request.container.width * request.container.height
    used_volume = sum(item.length * item.width * item.height for item in fitted_items)
    efficiency = (used_volume / container_volume * 100) if container_volume > 0 else 0
    
    return BinPackingResponse(
        placed_items=all_placed_items,
        total_items=len(all_placed_items),
        fitted_items=len(fitted_items),
        efficiency=round(efficiency, 2),
        total_weight=round(total_weight, 2),
        fitted_weight=round(fitted_weight, 2)
    )

# ==================== UPDATE MAIN ENDPOINTS ====================

# Update main endpoint to use smart algorithm selection
@router.post("/3d-bin-packing", response_model=BinPackingResponse)
async def calculate_3d_bin_packing(request: BinPackingRequest):
    """
    Main 3D bin packing endpoint with smart algorithm selection
    """
    # Redirect to smart algorithm selection
    return await calculate_3d_bin_packing_smart(request)

# Keep optimized endpoint as separate option
@router.post("/3d-bin-packing-optimized", response_model=BinPackingResponse)
async def calculate_3d_bin_packing_optimized(request: BinPackingRequest):
    """
    Legacy optimized endpoint - now redirects to smart selection
    """
    return await calculate_3d_bin_packing_smart(request)

# ==================== PERFORMANCE MONITORING ====================

@router.post("/3d-bin-packing-benchmark", response_model=BinPackingResponse)
async def benchmark_packing_algorithms(request: BinPackingRequest):
    """
    Benchmark different algorithms and return the best result
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
        
        cargo_items = []
        for item in request.items:
            cargo_items.append(CargoItem3D(
                id=item.id, name=item.name,
                length=item.length, width=item.width, height=item.height,
                weight=item.weight, quantity=item.quantity,
                non_stackable=item.non_stackable or False,
                non_rotatable=item.non_rotatable or False
            ))
        
        total_items = sum(item.quantity for item in request.items)
        
        # Run both algorithms if item count is reasonable
        if total_items <= 100:
            loop = asyncio.get_event_loop()
            
            # Run both algorithms concurrently
            standard_task = loop.run_in_executor(thread_pool, advanced_3d_packing, container, cargo_items)
            optimized_task = loop.run_in_executor(thread_pool, volume_optimized_3d_packing, container, cargo_items)
            
            standard_result, optimized_result = await asyncio.gather(standard_task, optimized_task)
            
            # Compare results and return the better one
            standard_fitted = len([item for item in standard_result if item.fitted])
            optimized_fitted = len([item for item in optimized_result if item.fitted])
            
            if optimized_fitted >= standard_fitted:
                best_result = optimized_result
                best_algorithm = "volume_optimized"
            else:
                best_result = standard_result
                best_algorithm = "standard"
            
            print(f"Benchmark: {best_algorithm} won (standard: {standard_fitted}, optimized: {optimized_fitted})")
        else:
            # For large sets, only use optimized
            loop = asyncio.get_event_loop()
            best_result = await loop.run_in_executor(thread_pool, volume_optimized_3d_packing, container, cargo_items)
            best_algorithm = "volume_optimized"
        
        # Convert to response format
        placed_items = []
        for item in best_result:
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
        raise HTTPException(status_code=500, detail=f"Benchmark failed: {str(e)}")

# [Keep all your existing equipment, cargo template, and saved layout endpoints unchanged]
# ==================== EXISTING ENDPOINTS CONTINUE BELOW ====================

# debug code
@router.post("/test-basic-packing")
async def test_basic_packing(request: BinPackingRequest):
    """
    Super simple test - just place first item at origin
    """
    print(f"TEST: Container = {request.container}")
    print(f"TEST: Items = {request.items}")
    
    # Just try to place the first item at (0,0,0)
    placed_items = []
    for i, item in enumerate(request.items):
        if i == 0:  # Only first item
            placed_items.append(PlacedItem(
                id=item.id,
                name=item.name,
                length=item.length,
                width=item.width,
                height=item.height,
                weight=item.weight,
                x=0, y=0, z=0,
                fitted=True,  # Force it to be fitted
                non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable
            ))
        else:
            placed_items.append(PlacedItem(
                id=item.id,
                name=item.name,
                length=item.length,
                width=item.width,
                height=item.height,
                weight=item.weight,
                x=0, y=0, z=0,
                fitted=False,
                non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable
            ))
    
    return BinPackingResponse(
        placed_items=placed_items,
        total_items=len(placed_items),
        fitted_items=1,
        efficiency=10.0,
        total_weight=100.0,
        fitted_weight=10.0
    )