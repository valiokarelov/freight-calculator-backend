# File: backend/api/equipment_models.py
# Part 2: Equipment Catalog Pydantic Models

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Dimensions, CargoItem, Container

class EquipmentResponse(BaseModel):
    """Response model for equipment catalog items"""
    id: int
    name: str
    full_name: str
    category: str  # aircraft, air-container, sea-vessel, sea-container, truck, van
    sub_category: Optional[str] = None  # freighter, pallet, dry-van, etc.
    type_code: str
    
    # Dimensions in requested units for display
    length: float
    width: float
    height: float
    unit: str
    
    # Capacities and specifications
    max_payload_kg: Optional[float] = None
    tare_weight_kg: Optional[float] = None
    cargo_volume_m3: Optional[float] = None
    
    # Door dimensions (if applicable)
    door_height: Optional[float] = None
    door_width: Optional[float] = None
    
    # Equipment-specific specifications
    specifications: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    
    # ULD/Container specific
    uld_count: Optional[int] = None
    uld_types: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    is_preset: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True

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

class CargoTemplateResponse(BaseModel):
    """Response model for cargo item templates"""
    id: int
    name: str
    category: str
    
    # Dimensions in requested units
    length: float
    width: float
    height: float
    weight: float
    unit: str
    weight_unit: str
    
    # Item properties
    stackable: bool = True
    fragile: bool = False
    non_rotatable: bool = False
    
    # Additional info
    description: Optional[str] = None
    typical_quantity: int = 1
    cost_per_unit: Optional[float] = None
    usage_count: int = 0
    
    # Metadata
    created_at: datetime
    
    class Config:
        from_attributes = True

class CargoTemplateCreate(BaseModel):
    """Create new cargo template"""
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    
    # Dimensions
    length: float = Field(..., gt=0)
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    unit: str = Field("in", pattern="^(in|ft|cm|m)$")
    weight_unit: str = Field("lb", pattern="^(kg|g|lb|oz)$")
    
    # Properties
    stackable: bool = True
    fragile: bool = False
    non_rotatable: bool = False
    description: Optional[str] = None
    typical_quantity: int = Field(1, gt=0)
    cost_per_unit: Optional[float] = Field(None, ge=0)

class SavedOptimizationResponse(BaseModel):
    """Response model for saved optimization results"""
    id: int
    name: str
    description: Optional[str] = None
    
    # Equipment reference
    equipment_id: Optional[int] = None
    equipment_name: Optional[str] = None
    
    # Summary statistics
    total_items: int
    placed_items: int
    volume_utilization: float
    weight_utilization: float
    efficiency_score: float
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    is_public: bool = False
    
    class Config:
        from_attributes = True

class SavedOptimizationCreate(BaseModel):
    """Create saved optimization"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    equipment_id: Optional[int] = None
    is_public: bool = False

# Conversion utility models
class ContainerFromEquipment(BaseModel):
    """Convert equipment catalog item to Container model"""
    
    @staticmethod
    def from_equipment_response(equipment: EquipmentResponse, container_id: str = None) -> Container:
        """Convert equipment response to Container model for optimization"""
        
        # Convert dimensions to centimeters (your system's standard)
        conversion_factors = {"in": 2.54, "ft": 30.48, "cm": 1.0, "m": 100.0}
        factor = conversion_factors.get(equipment.unit, 2.54)
        
        return Container(
            id=container_id or f"equipment-{equipment.id}",
            type="custom",  # Equipment catalog items are custom types
            dimensions=Dimensions(
                length=equipment.length * factor,
                width=equipment.width * factor,
                height=equipment.height * factor
            ),
            max_weight=equipment.max_payload_kg or 50000,  # Default if not specified
            name=equipment.full_name
        )

class CargoItemFromTemplate(BaseModel):
    """Convert cargo template to CargoItem model"""
    
    @staticmethod
    def from_template_response(template: CargoTemplateResponse, item_id: str = None, quantity: int = 1) -> CargoItem:
        """Convert template response to CargoItem model"""
        
        # Convert dimensions to centimeters
        length_conversions = {"in": 2.54, "ft": 30.48, "cm": 1.0, "m": 100.0}
        length_factor = length_conversions.get(template.unit, 2.54)
        
        # Convert weight to kilograms
        weight_conversions = {"kg": 1.0, "g": 0.001, "lb": 0.453592, "oz": 0.0283495}
        weight_factor = weight_conversions.get(template.weight_unit, 0.453592)
        
        return CargoItem(
            id=item_id or f"template-{template.id}-{int(datetime.now().timestamp())}",
            name=template.name,
            dimensions=Dimensions(
                length=template.length * length_factor,
                width=template.width * length_factor,
                height=template.height * length_factor
            ),
            weight=template.weight * weight_factor,
            quantity=quantity,
            stackable=template.stackable,
            fragile=template.fragile
        )

# Equipment categories and metadata
class EquipmentCategories(BaseModel):
    """Available equipment categories"""
    categories: List[str] = [
        "aircraft",
        "air-container", 
        "sea-vessel",
        "sea-container",
        "truck",
        "van"
    ]
    
    sub_categories: Dict[str, List[str]] = {
        "aircraft": ["freighter", "passenger-cargo", "cargo-combi"],
        "air-container": ["uld", "pallet", "container"],
        "sea-vessel": ["multipurpose", "container-ship", "bulk-carrier"],
        "sea-container": ["dry-van", "high-cube", "refrigerated", "open-top"],
        "truck": ["trailer", "box-truck", "flatbed"],
        "van": ["cargo-van", "delivery-van", "sprinter"]
    }

class CargoCategories(BaseModel):
    """Available cargo template categories"""
    categories: List[str] = [
        "electronics",
        "furniture",
        "appliances",
        "automotive",
        "industrial",
        "boxes",
        "pallets",
        "textiles",
        "food",
        "chemicals",
        "machinery"
    ]

# Statistics and summary models
class EquipmentStats(BaseModel):
    """Equipment catalog statistics"""
    total_equipment: int
    by_category: Dict[str, int]
    most_used: List[EquipmentResponse]
    recently_added: List[EquipmentResponse]

class TemplateStats(BaseModel):
    """Cargo template statistics"""
    total_templates: int
    by_category: Dict[str, int]
    most_used: List[CargoTemplateResponse]
    recently_added: List[CargoTemplateResponse]