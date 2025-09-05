# File: backend/api/database_models.py
# Part 3: SQLAlchemy Database Models

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()

class EquipmentCatalog(Base):
    """Equipment catalog for all cargo equipment types"""
    __tablename__ = "equipment_catalog"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # aircraft, air-container, sea-vessel, etc.
    sub_category = Column(String(50), nullable=True, index=True)  # freighter, pallet, dry-van, etc.
    type_code = Column(String(30), unique=True, nullable=False, index=True)
    
    # Primary dimensions (stored in centimeters for consistency)
    length_cm = Column(Float, nullable=False)
    width_cm = Column(Float, nullable=False) 
    height_cm = Column(Float, nullable=False)
    
    # Original units for display purposes
    original_unit = Column(String(10), default="in")
    
    # Weight specifications (in kilograms)
    max_payload_kg = Column(Float, nullable=True)
    tare_weight_kg = Column(Float, nullable=True)
    
    # Volume and capacity
    cargo_volume_m3 = Column(Float, nullable=True)
    
    # Equipment-specific specifications stored as JSON
    # This allows flexible storage of any equipment-specific data
    specifications = Column(JSON, nullable=True)
    
    # Additional descriptive properties
    description = Column(Text, nullable=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    
    # Operational specifications
    door_height_cm = Column(Float, nullable=True)
    door_width_cm = Column(Float, nullable=True)
    floor_height_cm = Column(Float, nullable=True)
    
    # Container/ULD specific fields
    uld_count = Column(Integer, nullable=True)
    uld_types = Column(JSON, nullable=True)  # Array of ULD type specifications
    
    # Status and metadata
    is_active = Column(Boolean, default=True, index=True)
    is_preset = Column(Boolean, default=True)  # Most catalog items are presets
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)  # User who added custom equipment
    
    # Relationships
    saved_optimizations = relationship("SavedOptimization", back_populates="equipment")
    
    def to_dict(self, target_unit: str = "in") -> Dict[str, Any]:
        """Convert to dictionary with unit conversion"""
        conversion_factors = {"cm": 1, "m": 100, "in": 2.54, "ft": 30.48}
        factor = conversion_factors.get(target_unit, 2.54)
        
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "category": self.category,
            "sub_category": self.sub_category,
            "type_code": self.type_code,
            "length": self.length_cm / factor,
            "width": self.width_cm / factor,
            "height": self.height_cm / factor,
            "unit": target_unit,
            "max_payload_kg": self.max_payload_kg,
            "tare_weight_kg": self.tare_weight_kg,
            "cargo_volume_m3": self.cargo_volume_m3,
            "door_height": self.door_height_cm / factor if self.door_height_cm else None,
            "door_width": self.door_width_cm / factor if self.door_width_cm else None,
            "specifications": self.specifications,
            "description": self.description,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "uld_count": self.uld_count,
            "uld_types": self.uld_types,
            "is_preset": self.is_preset,
            "created_at": self.created_at
        }

class CargoItemTemplate(Base):
    """Templates for common cargo items"""
    __tablename__ = "cargo_item_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    
    # Dimensions (stored in centimeters for consistency)
    length_cm = Column(Float, nullable=False)
    width_cm = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    
    # Original units for display
    original_unit = Column(String(10), default="in")
    original_weight_unit = Column(String(10), default="lb")
    
    # Item constraints and properties
    stackable = Column(Boolean, default=True)
    fragile = Column(Boolean, default=False)
    non_rotatable = Column(Boolean, default=False)
    
    # Additional properties
    description = Column(Text, nullable=True)
    typical_quantity = Column(Integer, default=1)
    cost_per_unit = Column(Float, nullable=True)  # For cost calculations
    
    # Metadata and usage tracking
    is_active = Column(Boolean, default=True, index=True)
    usage_count = Column(Integer, default=0)  # Track how often this template is used
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    def to_dict(self, target_unit: str = "in", target_weight_unit: str = "lb") -> Dict[str, Any]:
        """Convert to dictionary with unit conversion"""
        # Length conversion
        length_conversions = {"cm": 1, "m": 100, "in": 2.54, "ft": 30.48}
        length_factor = length_conversions.get(target_unit, 2.54)
        
        # Weight conversion  
        weight_conversions = {"kg": 1, "g": 0.001, "lb": 0.453592, "oz": 0.0283495}
        weight_factor = weight_conversions.get(target_weight_unit, 0.453592)
        
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "length": self.length_cm / length_factor,
            "width": self.width_cm / length_factor,
            "height": self.height_cm / length_factor,
            "weight": self.weight_kg / weight_factor,
            "unit": target_unit,
            "weight_unit": target_weight_unit,
            "stackable": self.stackable,
            "fragile": self.fragile,
            "non_rotatable": self.non_rotatable,
            "description": self.description,
            "typical_quantity": self.typical_quantity,
            "cost_per_unit": self.cost_per_unit,
            "usage_count": self.usage_count,
            "created_at": self.created_at
        }

class SavedOptimization(Base):
    """Saved optimization results and layouts"""
    __tablename__ = "saved_optimizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Equipment reference (optional - can be custom container)
    equipment_id = Column(Integer, ForeignKey("equipment_catalog.id"), nullable=True)
    equipment = relationship("EquipmentCatalog", back_populates="saved_optimizations")
    
    # Complete optimization data stored as JSON
    load_plan_data = Column(Text, nullable=False)  # JSON string of complete LoadPlan
    optimization_params = Column(JSON, nullable=True)  # Parameters used for optimization
    
    # Summary statistics for quick filtering and sorting
    total_items = Column(Integer, default=0)
    placed_items = Column(Integer, default=0)
    volume_utilization = Column(Float, default=0.0)  # Percentage
    weight_utilization = Column(Float, default=0.0)  # Percentage
    efficiency_score = Column(Float, default=0.0)    # Overall efficiency metric
    
    # Container/Equipment info (denormalized for quick access)
    container_type = Column(String(50), nullable=True)
    container_volume_m3 = Column(Float, nullable=True)
    container_payload_kg = Column(Float, nullable=True)
    
    # Metadata and sharing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)  # User ID or identifier
    is_public = Column(Boolean, default=False, index=True)  # Can be shared with others
    
    # Tags for categorization (JSON array)
    tags = Column(JSON, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "equipment_id": self.equipment_id,
            "equipment_name": self.equipment.full_name if self.equipment else None,
            "total_items": self.total_items,
            "placed_items": self.placed_items,
            "volume_utilization": self.volume_utilization,
            "weight_utilization": self.weight_utilization,
            "efficiency_score": self.efficiency_score,
            "container_type": self.container_type,
            "container_volume_m3": self.container_volume_m3,
            "container_payload_kg": self.container_payload_kg,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "is_public": self.is_public,
            "tags": self.tags
        }

class ULDSpecification(Base):
    """Detailed ULD (Unit Load Device) specifications for aircraft"""
    __tablename__ = "uld_specifications"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    uld_code = Column(String(20), nullable=False, index=True)  # IATA ULD code
    category = Column(String(30), nullable=False)  # container, pallet, bulk
    
    # Standard dimensions in centimeters
    length_cm = Column(Float, nullable=False)
    width_cm = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    
    # Weight specifications in kilograms
    max_payload_kg = Column(Float, nullable=False)
    tare_weight_kg = Column(Float, nullable=True)
    
    # Special contours and restrictions stored as JSON
    # Example: {"top_contour": {"left": "48x35", "right": "48x35"}}
    contours = Column(JSON, nullable=True)
    restrictions = Column(JSON, nullable=True)
    
    # Compatible aircraft (JSON array)
    compatible_aircraft = Column(JSON, nullable=True)
    
    # Floor specifications
    floor_height_cm = Column(Float, nullable=True)
    has_wheels = Column(Boolean, default=False)
    
    # Original units
    original_unit = Column(String(10), default="in")
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EquipmentUsageLog(Base):
    """Track equipment usage for analytics"""
    __tablename__ = "equipment_usage_log"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment_catalog.id"), nullable=False)
    equipment = relationship("EquipmentCatalog")
    
    # Usage details
    used_at = Column(DateTime, default=datetime.utcnow, index=True)
    used_by = Column(String(100), nullable=True)
    optimization_id = Column(Integer, ForeignKey("saved_optimizations.id"), nullable=True)
    
    # Usage context
    items_count = Column(Integer, nullable=True)
    utilization_achieved = Column(Float, nullable=True)
    session_id = Column(String(100), nullable=True)  # For tracking sessions

# Indexes for better query performance
from sqlalchemy import Index

# Create composite indexes for common queries
Index('idx_equipment_category_active', EquipmentCatalog.category, EquipmentCatalog.is_active)
Index('idx_equipment_type_active', EquipmentCatalog.sub_category, EquipmentCatalog.is_active)
Index('idx_templates_category_active', CargoItemTemplate.category, CargoItemTemplate.is_active)
Index('idx_optimizations_public_created', SavedOptimization.is_public, SavedOptimization.created_at)
Index('idx_optimizations_efficiency', SavedOptimization.efficiency_score)
Index('idx_usage_equipment_date', EquipmentUsageLog.equipment_id, EquipmentUsageLog.used_at)