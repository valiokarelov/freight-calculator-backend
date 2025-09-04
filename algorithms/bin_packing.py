#import numpy as np
from typing import List
from api.models import CargoItem, Container, PlacedItem, Position

def simple_bin_packing(items, container):
    """
    Simple first-fit bin packing algorithm
    This is a basic implementation - can be enhanced with more sophisticated algorithms
    """
    placed_items = []
    current_x = 0
    current_y = 0
    current_z = 0
    
    for item in items:
        for i in range(item.quantity):
            # Simple placement logic - place items in a row
            if current_x + item.dimensions.length <= container.dimensions.length:
                placed_item = PlacedItem(
                    **item.dict(),
                    position=Position(x=current_x, y=current_y, z=current_z),
                    placed=True
                )
                placed_items.append(placed_item)
                current_x += item.dimensions.length
            else:
                # Move to next row/layer if needed
                placed_item = PlacedItem(
                    **item.dict(),
                    position=Position(x=0, y=0, z=0),
                    placed=False  # Couldn't fit
                )
                placed_items.append(placed_item)
    
    return placed_items

def calculate_utilization(placed_items: List[PlacedItem], container: Container) -> dict:
    """Calculate container utilization statistics"""
    total_volume = 0
    total_weight = 0
    placed_count = 0
    
    container_volume = (
        container.dimensions.length * 
        container.dimensions.width * 
        container.dimensions.height
    ) / 1000000  # Convert to CBM
    
    for item in placed_items:
        if item.placed:
            item_volume = (
                item.dimensions.length * 
                item.dimensions.width * 
                item.dimensions.height
            ) / 1000000
            
            total_volume += item_volume
            total_weight += item.weight
            placed_count += 1
    
    return {
        "volume_utilization": (total_volume / container_volume) * 100 if container_volume > 0 else 0,
        "weight_utilization": (total_weight / container.max_weight) * 100 if container.max_weight > 0 else 0,
        "items_placed": placed_count,
        "total_items": len(placed_items),
        "efficiency": (placed_count / len(placed_items)) * 100 if placed_items else 0
    }