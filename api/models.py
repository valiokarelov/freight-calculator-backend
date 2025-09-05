# File: backend/api/models.py
# Complete Pydantic Models (Core + Equipment)

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
from datetime import datetime

# ==================== CORE MODELS (Your existing models) ====================

class Dimensions(BaseModel):
    length: float = Field(..., gt=0, description="Length in cm")
    width: float = Field(..., gt=0, description="Width in cm") 
    height: float = Field(..., gt=0, description="Height in cm")

class CargoItem(BaseModel):
    id: str
    name: str = "Cargo Item"
    dimensions: Dimensions
    weight: float = Field(..., gt=0, description="Weight in kg")
    quantity: int = Field(1, gt=0)
    stackable: bool = True
    fragile: bool = False
    
class Container(BaseModel):
    id: str = "container-1"
    type: str = Field(..., pattern="^(20ft|40ft|40hc|custom)$")
    dimensions: Dimensions
    max_weight: float = Field(..., gt=0, description="Maximum weight in kg")
    name: str = "Standard Container"

class Position(BaseModel):
    x: float
    y: float
    z: float

class PlacedItem(CargoItem):
    position: Position
    rotation: Optional[Position] = None
    placed: bool = False

class LoadPlan(BaseModel):
    id: str
    container: Container
    items: List[PlacedItem]
    utilization: dict
    timestamp: datetime
    
class OptimizationRequest(BaseModel):
    cargo_items: List[CargoItem]
    container: Container
    optimization_type: str = "volume"  # volume, weight, efficiency

# Enhanced request model with equipment catalog support
class EnhancedOptimizationRequest(BaseModel):
    cargo_items: List[CargoItem]
    container: Optional[Container] = None  # Optional when using equipment_id
    equipment_id: Optional[int] = None  # Use equipment from catalog instead
    optimization_type: str = "volume"
    save_result: bool = False
    result_name: Optional[str] = None

class OptimizationResult(BaseModel):
    load_plan: LoadPlan
    equipment_used: Optional[dict] = None  # Equipment info if used
    optimization_params: dict
    performance_metrics: dict
    saved_id: Optional[int] = None

# ==================== EQUIPMENT MODELS (For equipment_endpoints.py) ====================

# Equipment models that your equipment_endpoints.py is trying to import
class Equipment(BaseModel):
    """Base equipment model that matches your database structure"""
    id: Optional[int] = None
    name: str
    full_name: str
    category: str
    sub_category: Optional[str] = None
    type_code: str
    length_cm: float
    width_cm: float
    height_cm: float
    original_unit: str = "in"
    max_weight_kg: Optional[float] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True
    is_preset: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

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

# Cargo Template models
class CargoTemplate(BaseModel):
    """Base cargo template model"""
    id: Optional[int] = None
    name: str
    category: str
    length_cm: float
    width_cm: float
    height_cm: float
    weight_kg: float
    original_unit: str = "in"
    original_weight_unit: str = "lb"
    stackable: bool = True
    fragile: bool = False
    non_rotatable: bool = False
    description: Optional[str] = None
    typical_quantity: int = 1
    cost_per_unit: Optional[float] = None
    is_active: bool = True
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
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

# Saved Layout models
class SavedLayout(BaseModel):
    """Base saved layout model"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    equipment_id: int
    layout_data: str  # JSON string
    container_dimensions: str  # JSON string
    total_items: int = 0
    fitted_items: int = 0
    efficiency_percentage: float = 0.0
    total_weight_kg: float = 0.0
    fitted_weight_kg: float = 0.0
    is_public: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
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

# ==================== UTILITY AND CONVERSION MODELS ====================

class ContainerFromEquipment(BaseModel):
    """Convert equipment to Container model"""
    
    @staticmethod
    def from_equipment(equipment: Equipment, container_id: str = None) -> Container:
        """Convert equipment to Container model for optimization"""
        
        # Convert dimensions to your Container format (assumes cm input)
        return Container(
            id=container_id or f"equipment-{equipment.id}",
            type="custom",  # Equipment catalog items are custom types
            dimensions=Dimensions(
                length=equipment.length_cm,
                width=equipment.width_cm,
                height=equipment.height_cm
            ),
            max_weight=equipment.max_weight_kg or 50000,  # Default if not specified
            name=equipment.full_name
        )

class CargoItemFromTemplate(BaseModel):
    """Convert cargo template to CargoItem model"""
    
    @staticmethod
    def from_template(template: CargoTemplate, item_id: str = None, quantity: int = 1) -> CargoItem:
        """Convert template to CargoItem model"""
        
        return CargoItem(
            id=item_id or f"template-{template.id}-{int(datetime.now().timestamp())}",
            name=template.name,
            dimensions=Dimensions(
                length=template.length_cm,
                width=template.width_cm,
                height=template.height_cm
            ),
            weight=template.weight_kg,
            quantity=quantity,
            stackable=template.stackable,
            fragile=template.fragile
        )

# ==================== FILTER AND SEARCH MODELS ====================

class EquipmentFilter(BaseModel):
    """Filter parameters for equipment search"""
    category: Optional[str] = None
    sub_category: Optional[str] = None
    min_length: Optional[float] = None
    max_length: Optional[float] = None
    min_width: Optional[float] = None
    max_width: Optional[float] = None
    min_height: Optional[float] = None
    max_height: Optional[float] = None
    min_payload: Optional[float] = None
    max_payload: Optional[float] = None
    unit: str = "in"  # Unit for dimension filters

class CargoTemplateFilter(BaseModel):
    """Filter parameters for cargo template search"""
    category: Optional[str] = None
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    stackable: Optional[bool] = None
    fragile: Optional[bool] = None
    unit: str = "in"
    weight_unit: str = "lb"

# ==================== RESPONSE MODELS FOR API ====================

class EquipmentListResponse(BaseModel):
    """Response for equipment list endpoints"""
    equipment: List[EquipmentResponse]
    total: int
    categories: List[str]
    
class CargoTemplateListResponse(BaseModel):
    """Response for cargo template list endpoints"""
    templates: List[CargoTemplateResponse]
    total: int
    categories: List[str]

class SavedLayoutListResponse(BaseModel):
    """Response for saved layout list endpoints"""
    layouts: List[SavedLayoutResponse]
    total: int

# ==================== STATISTICS AND METADATA ====================

class EquipmentStats(BaseModel):
    """Equipment catalog statistics"""
    total_equipment: int
    by_category: Dict[str, int]
    most_used: List[str]  # Equipment type codes
    recently_added: List[str]

class SystemStats(BaseModel):
    """Overall system statistics"""
    equipment_count: int
    template_count: int
    saved_layouts_count: int
    categories: List[str]
    
# ==================== LEGACY COMPATIBILITY ====================

class LegacyPresetResponse(BaseModel):
    """Legacy preset format for backward compatibility"""
    presets: Dict[str, Dict[str, Any]]
    
    @staticmethod
    def from_equipment_list(equipment_list: List[Equipment]) -> "LegacyPresetResponse":
        """Convert equipment list to legacy preset format"""
        presets = {}
        
        for eq in equipment_list:
            if eq.is_preset:
                # Convert cm back to original units
                factor = 2.54 if eq.original_unit == "in" else 30.48 if eq.original_unit == "ft" else 1
                
                presets[eq.type_code] = {
                    "length": eq.length_cm / factor,
                    "width": eq.width_cm / factor,
                    "height": eq.height_cm / factor,
                    "name": eq.full_name,
                    "units": eq.original_unit
                }
        
        return LegacyPresetResponse(presets=presets)