# File: api/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
from datetime import datetime

# ==================== BIN PACKING MODELS ====================

class CargoItem3D(BaseModel):
    id: str
    name: str
    length: float  # cm
    width: float   # cm
    height: float  # cm
    weight: float  # kg
    quantity: int = 1
    non_stackable: bool = False
    non_rotatable: bool = False

class Container3D(BaseModel):
    length: float  # cm
    width: float   # cm
    height: float  # cm
    max_weight: float = 50000  # kg

class PlacedItem3D(CargoItem3D):
    x: float
    y: float
    z: float
    fitted: bool
    rotated: bool = False

class Container(BaseModel):
    length: float
    width: float
    height: float
    max_weight: Optional[float] = 50000

class BinPackingItem(BaseModel):
    id: str
    name: str
    length: float
    width: float
    height: float
    weight: float
    quantity: int = 1
    non_stackable: Optional[bool] = False
    non_rotatable: Optional[bool] = False

class PlacedItem(BaseModel):
    id: str
    name: str
    length: float
    width: float
    height: float
    weight: float
    x: float
    y: float
    z: float
    fitted: bool
    non_stackable: Optional[bool] = False
    non_rotatable: Optional[bool] = False

class BinPackingRequest(BaseModel):
    container: Container
    items: List[BinPackingItem]

class BinPackingResponse(BaseModel):
    placed_items: List[PlacedItem]
    total_items: int
    fitted_items: int
    efficiency: float
    total_weight: float
    fitted_weight: float
    processing_time: Optional[float] = None

class PackingRequest(BaseModel):
    container: Container3D
    items: List[CargoItem3D]

class PackingResponse(BaseModel):
    placed_items: List[PlacedItem3D]
    stats: dict

# ==================== CORE MODELS ====================

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
    
class Position(BaseModel):
    x: float
    y: float
    z: float

class PlacedCargoItem(CargoItem):
    position: Position
    rotation: Optional[Position] = None
    placed: bool = False

class LoadPlan(BaseModel):
    id: str
    container: Container
    items: List[PlacedCargoItem]
    utilization: dict
    timestamp: datetime
    
class OptimizationRequest(BaseModel):
    cargo_items: List[CargoItem]
    container: Container
    optimization_type: str = "volume"  # volume, weight, efficiency

class EnhancedOptimizationRequest(BaseModel):
    cargo_items: List[CargoItem]
    container: Optional[Container] = None
    equipment_id: Optional[int] = None
    optimization_type: str = "volume"
    save_result: bool = False
    result_name: Optional[str] = None

class OptimizationResult(BaseModel):
    load_plan: LoadPlan
    equipment_used: Optional[dict] = None
    optimization_params: dict
    performance_metrics: dict
    saved_id: Optional[int] = None

# ==================== EQUIPMENT MODELS ====================

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

class Equipment(BaseModel):
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

# ==================== CARGO TEMPLATE MODELS ====================

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

class CargoTemplate(BaseModel):
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

# ==================== SAVED LAYOUT MODELS ====================

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

class SavedLayout(BaseModel):
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

# ==================== UTILITY MODELS ====================

class ContainerFromEquipment(BaseModel):
    @staticmethod
    def from_equipment(equipment: Equipment, container_id: str = None) -> Container:
        return Container(
            id=container_id or f"equipment-{equipment.id}",
            type="custom",
            dimensions=Dimensions(
                length=equipment.length_cm,
                width=equipment.width_cm,
                height=equipment.height_cm
            ),
            max_weight=equipment.max_weight_kg or 50000,
            name=equipment.full_name
        )

class CargoItemFromTemplate(BaseModel):
    @staticmethod
    def from_template(template: CargoTemplate, item_id: str = None, quantity: int = 1) -> CargoItem:
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

# ==================== FILTER MODELS ====================

class EquipmentFilter(BaseModel):
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
    unit: str = "in"

class CargoTemplateFilter(BaseModel):
    category: Optional[str] = None
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    stackable: Optional[bool] = None
    fragile: Optional[bool] = None
    unit: str = "in"
    weight_unit: str = "lb"

# ==================== RESPONSE MODELS ====================

class EquipmentListResponse(BaseModel):
    equipment: List[EquipmentResponse]
    total: int
    categories: List[str]
    
class CargoTemplateListResponse(BaseModel):
    templates: List[CargoTemplateResponse]
    total: int
    categories: List[str]

class SavedLayoutListResponse(BaseModel):
    layouts: List[SavedLayoutResponse]
    total: int

class EquipmentStats(BaseModel):
    total_equipment: int
    by_category: Dict[str, int]
    most_used: List[str]
    recently_added: List[str]

class SystemStats(BaseModel):
    equipment_count: int
    template_count: int
    saved_layouts_count: int
    categories: List[str]
    
class LegacyPresetResponse(BaseModel):
    presets: Dict[str, Dict[str, Any]]
    
    @staticmethod
    def from_equipment_list(equipment_list: List[Equipment]) -> "LegacyPresetResponse":
        presets = {}
        
        for eq in equipment_list:
            if eq.is_preset:
                factor = 2.54 if eq.original_unit == "in" else 30.48 if eq.original_unit == "ft" else 1
                
                presets[eq.type_code] = {
                    "length": eq.length_cm / factor,
                    "width": eq.width_cm / factor,
                    "height": eq.height_cm / factor,
                    "name": eq.full_name,
                    "units": eq.original_unit
                }
        
        return LegacyPresetResponse(presets=presets)