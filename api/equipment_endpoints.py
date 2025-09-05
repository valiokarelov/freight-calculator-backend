# Phase 2 - Equipment Management API Endpoints
# File: backend/api/equipment_endpoints.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from api.database import get_db
from api.database_models import EquipmentCatalog, CargoItemTemplate, SavedOptimization
import json
from datetime import datetime
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

security = HTTPBearer()
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Get API key from environment variable
    expected_key = os.environ.get("API_KEY", "your-fallback-secret-key")
    if credentials.credentials != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

router = APIRouter(prefix="/api/equipment", tags=["equipment"])

# Pydantic models for request/response
class EquipmentBase(BaseModel):
    name: str
    category: str
    length_cm: float
    width_cm: float
    height_cm: float
    original_unit: str = "in"
    max_weight_kg: Optional[float] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None

class EquipmentCreate(EquipmentBase):
    type_code: str

class EquipmentResponse(EquipmentBase):
    id: int
    type_code: str
    volume_cubic_cm: float
    is_active: bool
    is_preset: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CargoTemplateBase(BaseModel):
    name: str
    category: str
    length_cm: float
    width_cm: float  
    height_cm: float
    weight_kg: float
    original_unit: str = "in"
    original_weight_unit: str = "lb"
    non_stackable: bool = False
    non_rotatable: bool = False
    fragile: bool = False
    description: Optional[str] = None
    typical_quantity: int = 1
    cost_per_unit: Optional[float] = None

class CargoTemplateResponse(CargoTemplateBase):
    id: int
    is_active: bool
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class SavedLayoutCreate(BaseModel):
    name: str
    equipment_id: int
    description: Optional[str] = None
    layout_data: str  # JSON string
    container_dimensions: str  # JSON string
    total_items: int = 0
    fitted_items: int = 0
    efficiency_percentage: float = 0.0
    total_weight_kg: float = 0.0
    fitted_weight_kg: float = 0.0
    is_public: bool = False

class SavedLayoutResponse(SavedLayoutCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    equipment_name: str
    
    class Config:
        from_attributes = True

# Equipment endpoints
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
    for field, value in equipment_data.model_dump()(exclude_unset=True).items():
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
    api_key: str = Depends(verify_api_key)  # Add this line
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

# Cargo template endpoints
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

# Saved layouts endpoints
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
    
    layout = SavedOptimization(**layout_data.model_dump()())
    
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

# Utility endpoints
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
    equipment = db.query(EquipmentCatalog).filter(EquipmentCatalog.is_preset == True, EquipmentCatalog.is_active == True).all()
    
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