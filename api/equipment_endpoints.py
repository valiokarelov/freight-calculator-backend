# File: api/equipment_endpoints.py - Fixed version
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

# Import only the working algorithm
from algorithms.advanced_packing import advanced_3d_packing

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

# ==================== MAIN WORKING ENDPOINTS ====================

@router.post("/3d-bin-packing", response_model=BinPackingResponse)
async def calculate_3d_bin_packing(request: BinPackingRequest):
    """
    Main 3D bin packing endpoint using the working advanced algorithm
    """
    try:
        print(f"Processing {len(request.items)} item types...")
        
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
        
        print(f"Total individual items: {total_items}")
        print(f"Container: {container.length} x {container.width} x {container.height} cm")
        
        # Use working algorithm in thread pool
        loop = asyncio.get_event_loop()
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
        
        print(f"Results: {len(fitted_items)}/{len(placed_items)} items fitted ({efficiency:.1f}% efficiency)")
        
        return BinPackingResponse(
            placed_items=placed_items,
            total_items=len(placed_items),
            fitted_items=len(fitted_items),
            efficiency=round(efficiency, 2),
            total_weight=round(total_weight, 2),
            fitted_weight=round(fitted_weight, 2)
        )
        
    except Exception as e:
        print(f"Error in main packing endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Packing calculation failed: {str(e)}")

@router.post("/3d-bin-packing-smart", response_model=BinPackingResponse)
async def calculate_3d_bin_packing_smart(request: BinPackingRequest):
    """
    Smart endpoint - redirects to main working algorithm
    """
    return await calculate_3d_bin_packing(request)

# ==================== DEBUG AND TEST ENDPOINTS ====================

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

# ==================== LEGACY 3D PACKING ENDPOINT ====================

@router.post("/3d-packing", response_model=PackingResponse)
async def optimize_3d_packing(request: PackingRequest):
    """
    Legacy 3D packing endpoint for backward compatibility
    """
    try:
        # Use the advanced packing algorithm
        packed_items = await asyncio.get_event_loop().run_in_executor(
            thread_pool,
            advanced_3d_packing,
            request.container,
            request.items
        )
        
        # Calculate statistics
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

@router.get("/containers/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment_by_id(equipment_id: int, db: Session = Depends(get_db)):
    """Get specific equipment by ID"""
    equipment = db.query(EquipmentCatalog).filter(EquipmentCatalog.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return EquipmentResponse.model_validate(equipment)

@router.get("/containers/code/{type_code}", response_model=EquipmentResponse)
async def get_equipment_by_code(type_code: str, db: Session = Depends(get_db)):
    """Get equipment by type code (for backward compatibility)"""
    equipment = db.query(EquipmentCatalog).filter(EquipmentCatalog.type_code == type_code).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return EquipmentResponse.model_validate(equipment)

@router.post("/containers", response_model=EquipmentResponse)
async def create_custom_equipment(
    equipment_data: EquipmentCreate, 
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Create custom equipment/container"""
    
    # Check if type_code already exists
    existing = db.query(EquipmentCatalog).filter(EquipmentCatalog.type_code == equipment_data.type_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Type code already exists")
    
    # Calculate volume
    volume = equipment_data.length_cm * equipment_data.width_cm * equipment_data.height_cm
    
    # Create equipment
    equipment = EquipmentCatalog(
        **equipment_data.model_dump(),
        volume_cubic_cm=volume,
        is_preset=False,
        is_active=True
    )
    
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    
    return EquipmentResponse.model_validate(equipment)

@router.put("/containers/{equipment_id}", response_model=EquipmentResponse) 
async def update_equipment(
    equipment_id: int,
    equipment_data: EquipmentBase,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update equipment (only custom equipment can be modified)"""
    equipment = db.query(EquipmentCatalog).filter(EquipmentCatalog.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    if equipment.is_preset:
        raise HTTPException(status_code=400, detail="Cannot modify preset equipment")
    
    # Update fields
    for field, value in equipment_data.model_dump(exclude_unset=True).items():
        setattr(equipment, field, value)
    
    # Recalculate volume
    equipment.volume_cubic_cm = equipment.length_cm * equipment.width_cm * equipment.height_cm
    equipment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(equipment)
    
    return EquipmentResponse.model_validate(equipment)

@router.delete("/containers/{equipment_id}")
async def delete_equipment(
    equipment_id: int, 
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Delete custom equipment (soft delete by setting inactive)"""
    equipment = db.query(EquipmentCatalog).filter(EquipmentCatalog.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    if equipment.is_preset:
        raise HTTPException(status_code=400, detail="Cannot delete preset equipment")
    
    equipment.is_active = False
    equipment.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Equipment deleted successfully"}

# ==================== CARGO TEMPLATE ENDPOINTS ====================

@router.get("/cargo-templates", response_model=List[CargoTemplateResponse])
async def get_cargo_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """Get all cargo templates"""
    query = db.query(CargoItemTemplate).filter(CargoItemTemplate.is_active == True)
    
    if category:
        query = query.filter(CargoItemTemplate.category == category)
    
    templates = query.order_by(CargoItemTemplate.usage_count.desc(), CargoItemTemplate.name).all()
    return [CargoTemplateResponse.model_validate(template) for template in templates]

@router.post("/cargo-templates", response_model=CargoTemplateResponse)
async def create_cargo_template(
    template_data: CargoTemplateBase,
    db: Session = Depends(get_db)
):
    """Create new cargo template"""
    template = CargoItemTemplate(**template_data.model_dump())
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return CargoTemplateResponse.model_validate(template)

@router.put("/cargo-templates/{template_id}/use")
async def increment_template_usage(template_id: int, db: Session = Depends(get_db)):
    """Increment usage count when template is used"""
    template = db.query(CargoItemTemplate).filter(CargoItemTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.usage_count += 1
    db.commit()
    
    return {"message": "Usage count updated"}

# ==================== SAVED LAYOUTS ENDPOINTS ====================

@router.get("/saved-layouts", response_model=List[SavedLayoutResponse])
async def get_saved_layouts(
    equipment_id: Optional[int] = Query(None, description="Filter by equipment"),
    public_only: bool = Query(False, description="Show only public layouts"),
    db: Session = Depends(get_db)
):
    """Get saved layouts"""
    query = db.query(SavedOptimization).join(EquipmentCatalog)
    
    if equipment_id:
        query = query.filter(SavedOptimization.equipment_id == equipment_id)
    
    if public_only:
        query = query.filter(SavedOptimization.is_public == True)
    
    layouts = query.order_by(SavedOptimization.created_at.desc()).all()
    
    # Add equipment name to response
    result = []
    for layout in layouts:
        layout_dict = {
            **layout.__dict__,
            "equipment_name": layout.equipment.name
        }
        result.append(SavedLayoutResponse(**layout_dict))
    
    return result

@router.post("/saved-layouts", response_model=SavedLayoutResponse)
async def save_layout(layout_data: SavedLayoutCreate, db: Session = Depends(get_db)):
    """Save a cargo layout"""
    
    # Verify equipment exists
    equipment = db.query(EquipmentCatalog).filter(EquipmentCatalog.id == layout_data.equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Validate JSON data
    try:
        json.loads(layout_data.layout_data)
        json.loads(layout_data.container_dimensions)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    
    layout = SavedOptimization(**layout_data.model_dump())
    
    db.add(layout)
    db.commit()
    db.refresh(layout)
    
    # Add equipment name for response
    layout_dict = {
        **layout.__dict__,
        "equipment_name": equipment.name
    }
    
    return SavedLayoutResponse(**layout_dict)

@router.get("/saved-layouts/{layout_id}", response_model=SavedLayoutResponse)
async def get_saved_layout(layout_id: int, db: Session = Depends(get_db)):
    """Get specific saved layout"""
    layout = db.query(SavedOptimization).filter(SavedOptimization.id == layout_id).first()
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    layout_dict = {
        **layout.__dict__,
        "equipment_name": layout.equipment.name
    }
    
    return SavedLayoutResponse(**layout_dict)

@router.delete("/saved-layouts/{layout_id}")
async def delete_saved_layout(layout_id: int, db: Session = Depends(get_db)):
    """Delete saved layout"""
    layout = db.query(SavedOptimization).filter(SavedOptimization.id == layout_id).first()
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    db.delete(layout)
    db.commit()
    
    return {"message": "Layout deleted successfully"}

# ==================== UTILITY ENDPOINTS ====================

@router.get("/categories")
async def get_equipment_categories(db: Session = Depends(get_db)):
    """Get all equipment categories"""
    categories = db.query(EquipmentCatalog.category).distinct().all()
    return [cat[0] for cat in categories]

@router.get("/cargo-categories")
async def get_cargo_categories(db: Session = Depends(get_db)):
    """Get all cargo template categories"""
    categories = db.query(CargoItemTemplate.category).distinct().all()
    return [cat[0] for cat in categories]

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