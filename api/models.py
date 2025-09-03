from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime

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