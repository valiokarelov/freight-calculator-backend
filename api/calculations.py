from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json

router = APIRouter()

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

class PackingRequest(BaseModel):
    container: Container3D
    items: List[CargoItem3D]

class PackingResponse(BaseModel):
    placed_items: List[PlacedItem3D]
    stats: dict

# Models for the new endpoint (matching frontend expectations)
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

# Keep your existing endpoint but fix the function call
@router.post("/3d-packing", response_model=PackingResponse)
async def optimize_3d_packing(request: PackingRequest):
    try:
        # Convert to new format and use the advanced algorithm
        container = Container(
            length=request.container.length,
            width=request.container.width,
            height=request.container.height,
            max_weight=request.container.max_weight
        )
        
        # Expand items by quantity and convert to PlacedItem format
        expanded_items = []
        for item in request.items:
            for i in range(item.quantity):
                expanded_items.append(PlacedItem(
                    id=f"{item.id}_{i}" if item.quantity > 1 else item.id,
                    name=f"{item.name} #{i+1}" if item.quantity > 1 else item.name,
                    length=item.length,
                    width=item.width,
                    height=item.height,
                    weight=item.weight,
                    x=0, y=0, z=0,
                    fitted=False,
                    non_stackable=item.non_stackable,
                    non_rotatable=item.non_rotatable
                ))
        
        # Use the advanced packing algorithm
        packed_items = advanced_bin_packing(container, expanded_items)
        
        # Convert back to PlacedItem3D format
        placed_items_3d = []
        for item in packed_items:
            placed_items_3d.append(PlacedItem3D(
                id=item.id,
                name=item.name,
                length=item.length,
                width=item.width,
                height=item.height,
                weight=item.weight,
                quantity=1,
                non_stackable=item.non_stackable or False,
                non_rotatable=item.non_rotatable or False,
                x=item.x,
                y=item.y,
                z=item.z,
                fitted=item.fitted,
                rotated=False  # You can add rotation detection logic if needed
            ))
        
        # Calculate statistics
        fitted_items = [item for item in placed_items_3d if item.fitted]
        total_volume = request.container.length * request.container.width * request.container.height
        used_volume = sum(item.length * item.width * item.height for item in fitted_items)
        
        stats = {
            "total_items": len(placed_items_3d),
            "fitted_items": len(fitted_items),
            "unfitted_items": len(placed_items_3d) - len(fitted_items),
            "space_efficiency": round((used_volume / total_volume * 100) if total_volume > 0 else 0, 2),
            "total_weight": round(sum(item.weight for item in placed_items_3d), 2),
            "fitted_weight": round(sum(item.weight for item in fitted_items), 2)
        }
        
        return PackingResponse(placed_items=placed_items_3d, stats=stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Packing calculation failed: {str(e)}")

# New endpoint that matches your frontend exactly
@router.post("/3d-bin-packing", response_model=BinPackingResponse)
async def calculate_3d_bin_packing(request: BinPackingRequest):
    """
    Advanced 3D bin packing algorithm with tight packing optimization
    """
    try:
        container = request.container
        items = request.items
        
        # Expand items by quantity
        expanded_items = []
        for item in items:
            for i in range(item.quantity):
                expanded_items.append(PlacedItem(
                    id=f"{item.id}_{i}" if item.quantity > 1 else item.id,
                    name=f"{item.name} #{i+1}" if item.quantity > 1 else item.name,
                    length=item.length,
                    width=item.width,
                    height=item.height,
                    weight=item.weight,
                    x=0, y=0, z=0,
                    fitted=False,
                    non_stackable=item.non_stackable,
                    non_rotatable=item.non_rotatable
                ))
        
        # Advanced packing algorithm
        placed_items = advanced_bin_packing(container, expanded_items)
        
        # Calculate statistics
        fitted_items = [item for item in placed_items if item.fitted]
        total_weight = sum(item.weight for item in placed_items)
        fitted_weight = sum(item.weight for item in fitted_items)
        
        # Calculate volume efficiency
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
        raise HTTPException(status_code=500, detail=f"Packing calculation failed: {str(e)}")

def advanced_bin_packing(container: Container, items: List[PlacedItem]) -> List[PlacedItem]:
    """
    Enhanced 3D bin packing with adjacent placement and tight packing optimization
    """
    placed = []
    
    # Sort items by volume (largest first)
    sorted_items = sorted(items, key=lambda x: x.length * x.width * x.height, reverse=True)
    
    def overlaps(a, b):
        """Check if two items overlap"""
        return not (
            a.x >= b.x + b.length - 0.01 or
            a.x + a.length <= b.x + 0.01 or
            a.y >= b.y + b.width - 0.01 or
            a.y + a.width <= b.y + 0.01 or
            a.z >= b.z + b.height - 0.01 or
            a.z + a.height <= b.z + 0.01
        )
    
    def find_best_position(item, L, W, H):
        """Find the best position for an item using adjacency-based tight packing"""
        candidates = []
        
        # Generate adjacent positions
        adjacent_positions = []
        
        if not placed:
            adjacent_positions.append({'x': 0, 'y': 0, 'z': 0})
        else:
            for existing in placed:
                # Right side
                if existing.x + existing.length + L <= container.length:
                    adjacent_positions.append({
                        'x': existing.x + existing.length,
                        'y': existing.y,
                        'z': existing.z
                    })
                
                # Front side
                if existing.y + existing.width + W <= container.width:
                    adjacent_positions.append({
                        'x': existing.x,
                        'y': existing.y + existing.width,
                        'z': existing.z
                    })
                
                # Top (if stacking allowed)
                if (not existing.non_stackable and not item.non_stackable and 
                    existing.z + existing.height + H <= container.height):
                    adjacent_positions.append({
                        'x': existing.x,
                        'y': existing.y,
                        'z': existing.z + existing.height
                    })
        
        # Test each position
        for pos in adjacent_positions:
            # Create test item
            test_item = PlacedItem(
                id=item.id, name=item.name, weight=item.weight,
                length=L, width=W, height=H,
                x=pos['x'], y=pos['y'], z=pos['z'],
                fitted=True,
                non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable
            )
            
            # Check bounds
            if (pos['x'] + L > container.length or 
                pos['y'] + W > container.width or 
                pos['z'] + H > container.height):
                continue
            
            # Check collisions
            if any(overlaps(test_item, p) for p in placed):
                continue
            
            # Check stacking support
            if pos['z'] > 0:
                if item.non_stackable:
                    continue
                
                support_area = 0
                required_support = L * W * 0.7  # 70% support required
                
                for p in placed:
                    if p.non_stackable:
                        continue
                    
                    if abs(p.z + p.height - pos['z']) < 0.1:
                        overlap_x = min(pos['x'] + L, p.x + p.length) - max(pos['x'], p.x)
                        overlap_y = min(pos['y'] + W, p.y + p.width) - max(pos['y'], p.y)
                        
                        if overlap_x > 0 and overlap_y > 0:
                            support_area += overlap_x * overlap_y
                
                if support_area < required_support:
                    continue
            
            # Calculate adjacency score
            touching_items = 0
            for p in placed:
                touching_x = (abs(p.x + p.length - pos['x']) < 0.1) or (abs(pos['x'] + L - p.x) < 0.1)
                touching_y = (abs(p.y + p.width - pos['y']) < 0.1) or (abs(pos['y'] + W - p.y) < 0.1)
                touching_z = (abs(p.z + p.height - pos['z']) < 0.1) or (abs(pos['z'] + H - p.z) < 0.1)
                
                aligned_x = (pos['x'] < p.x + p.length and pos['x'] + L > p.x)
                aligned_y = (pos['y'] < p.y + p.width and pos['y'] + W > p.y)
                aligned_z = (pos['z'] < p.z + p.height and pos['z'] + H > p.z)
                
                if ((touching_x and aligned_y and aligned_z) or
                    (touching_y and aligned_x and aligned_z) or
                    (touching_z and aligned_x and aligned_y)):
                    touching_items += 1
            
            # Priority: favor positions with more adjacent items, then lower positions
            priority = -(touching_items * 1000) + pos['z'] * 100 + pos['y'] * 10 + pos['x']
            
            candidates.append({
                'item': test_item,
                'priority': priority,
                'touching_items': touching_items
            })
        
        # Fallback: grid search if no adjacent positions work
        if not candidates:
            step = max(1, min(L, W, H) / 4)
            z_steps = range(0, int(container.height - H) + 1, max(1, int(step)))
            y_steps = range(0, int(container.width - W) + 1, max(1, int(step)))
            x_steps = range(0, int(container.length - L) + 1, max(1, int(step)))
            
            for z in z_steps:
                for y in y_steps:
                    for x in x_steps:
                        test_item = PlacedItem(
                            id=item.id, name=item.name, weight=item.weight,
                            length=L, width=W, height=H,
                            x=float(x), y=float(y), z=float(z), fitted=True,
                            non_stackable=item.non_stackable,
                            non_rotatable=item.non_rotatable
                        )
                        
                        if any(overlaps(test_item, p) for p in placed):
                            continue
                        
                        # Basic stacking validation for grid search
                        if z > 0 and item.non_stackable:
                            continue
                        
                        priority = z * 100 + y * 10 + x
                        candidates.append({
                            'item': test_item,
                            'priority': priority,
                            'touching_items': 0
                        })
        
        # Return best candidate
        if candidates:
            candidates.sort(key=lambda x: x['priority'])
            return candidates[0]['item']
        
        return None
    
    # Place each item
    for item in sorted_items:
        best_position = None
        
        # Try different orientations
        orientations = []
        if item.non_rotatable:
            orientations = [(item.length, item.width, item.height)]
        else:
            orientations = [
                (item.length, item.width, item.height),
                (item.width, item.length, item.height)
            ]
        
        for L, W, H in orientations:
            if L <= container.length and W <= container.width and H <= container.height:
                position = find_best_position(item, L, W, H)
                if position:
                    best_position = position
                    break
        
        if best_position:
            placed.append(best_position)
            # Update original item
            for original_item in sorted_items:
                if original_item.id == item.id:
                    original_item.x = best_position.x
                    original_item.y = best_position.y
                    original_item.z = best_position.z
                    original_item.length = best_position.length
                    original_item.width = best_position.width
                    original_item.height = best_position.height
                    original_item.fitted = True
                    break
    
    return sorted_items