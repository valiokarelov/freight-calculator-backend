from typing import List, Tuple, Optional
import math
from api.models import CargoItem3D, Container3D, PlacedItem3D

def advanced_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Advanced 3D bin packing with multiple optimization strategies
    """
    # Expand quantity to individual items
    individual_items = []
    for item in items:
        for i in range(item.quantity):
            individual_items.append(PlacedItem3D(
                **item.dict(exclude={'quantity'}),
                id=f"{item.id}_{i+1}" if item.quantity > 1 else item.id,
                x=0, y=0, z=0, fitted=False, rotated=False
            ))
    
    # Sort by volume (largest first) and weight
    individual_items.sort(key=lambda x: (
        x.length * x.width * x.height,  # Volume
        x.weight  # Weight as tiebreaker
    ), reverse=True)
    
    placed_items = []
    
    for item in individual_items:
        best_position = find_best_position_advanced(container, placed_items, item)
        
        if best_position:
            item.x = best_position['x']
            item.y = best_position['y']
            item.z = best_position['z']
            item.length = best_position['length']
            item.width = best_position['width']
            item.height = best_position['height']
            item.fitted = True
            item.rotated = best_position.get('rotated', False)
            placed_items.append(item)
    
    return individual_items

def find_best_position_advanced(container: Container3D, placed_items: List[PlacedItem3D], item: PlacedItem3D) -> Optional[dict]:
    """
    Find optimal position using multiple strategies
    """
    # Generate possible orientations
    orientations = get_orientations(item)
    
    # Generate candidate positions
    candidates = []
    
    for orientation in orientations:
        L, W, H = orientation['length'], orientation['width'], orientation['height']
        
        # Skip if doesn't fit in container
        if L > container.length or W > container.width or H > container.height:
            continue
            
        # Strategy 1: Adjacent placement (tight packing)
        adjacent_positions = get_adjacent_positions(container, placed_items, L, W, H)
        
        for pos in adjacent_positions:
            if is_valid_position(container, placed_items, pos, L, W, H, item):
                score = calculate_position_score(container, placed_items, pos, L, W, H)
                candidates.append({
                    'x': pos[0], 'y': pos[1], 'z': pos[2],
                    'length': L, 'width': W, 'height': H,
                    'score': score, 'rotated': orientation.get('rotated', False)
                })
        
        # Strategy 2: Grid-based placement (fallback)
        if not candidates:
            grid_positions = get_grid_positions(container, L, W, H)
            
            for pos in grid_positions:
                if is_valid_position(container, placed_items, pos, L, W, H, item):
                    score = calculate_position_score(container, placed_items, pos, L, W, H)
                    candidates.append({
                        'x': pos[0], 'y': pos[1], 'z': pos[2],
                        'length': L, 'width': W, 'height': H,
                        'score': score, 'rotated': orientation.get('rotated', False)
                    })
                    break  # Take first valid grid position
    
    # Return best candidate
    return min(candidates, key=lambda x: x['score']) if candidates else None

def get_orientations(item: PlacedItem3D) -> List[dict]:
    """Get possible orientations for an item"""
    if item.non_rotatable:
        return [{'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False}]
    
    return [
        {'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False},
        {'length': item.width, 'width': item.length, 'height': item.height, 'rotated': True},
    ]

def get_adjacent_positions(container: Container3D, placed_items: List[PlacedItem3D], L: float, W: float, H: float) -> List[Tuple[float, float, float]]:
    """Generate positions adjacent to existing items"""
    positions = set()
    
    if not placed_items:
        positions.add((0, 0, 0))
        return list(positions)
    
    for item in placed_items:
        # Right side
        if item.x + item.length + L <= container.length:
            positions.add((item.x + item.length, item.y, item.z))
        
        # Front side  
        if item.y + item.width + W <= container.width:
            positions.add((item.x, item.y + item.width, item.z))
        
        # Top (if stacking allowed)
        if not item.non_stackable and item.z + item.height + H <= container.height:
            positions.add((item.x, item.y, item.z + item.height))
    
    return list(positions)

def is_valid_position(container: Container3D, placed_items: List[PlacedItem3D], 
                     pos: Tuple[float, float, float], L: float, W: float, H: float, 
                     item: PlacedItem3D) -> bool:
    """Check if position is valid (no collisions, proper support)"""
    x, y, z = pos
    
    # Check container bounds
    if x + L > container.length or y + W > container.width or z + H > container.height:
        return False
    
    # Check collisions
    for existing in placed_items:
        if (x < existing.x + existing.length - 0.01 and x + L > existing.x + 0.01 and
            y < existing.y + existing.width - 0.01 and y + W > existing.y + 0.01 and
            z < existing.z + existing.height - 0.01 and z + H > existing.z + 0.01):
            return False
    
    # Check support if not on ground
    if z > 0:
        if item.non_stackable:
            return False
        
        support_area = 0
        required_support = L * W * 0.7  # 70% support required
        
        for existing in placed_items:
            if existing.non_stackable:
                continue
                
            # Check if item provides support at our level
            if abs(existing.z + existing.height - z) < 0.1:
                overlap_x = min(x + L, existing.x + existing.length) - max(x, existing.x)
                overlap_y = min(y + W, existing.y + existing.width) - max(y, existing.y)
                
                if overlap_x > 0 and overlap_y > 0:
                    support_area += overlap_x * overlap_y
        
        return support_area >= required_support
    
    return True

def calculate_position_score(container: Container3D, placed_items: List[PlacedItem3D], 
                           pos: Tuple[float, float, float], L: float, W: float, H: float) -> float:
    """Calculate position score (lower is better)"""
    x, y, z = pos
    
    # Prefer lower positions and positions closer to back-left corner
    base_score = z * 100 + y * 10 + x
    
    # Bonus for tight packing (adjacent to existing items)
    adjacency_bonus = 0
    for existing in placed_items:
        # Check if touching
        if ((abs(existing.x + existing.length - x) < 0.1 or abs(x + L - existing.x) < 0.1) and
            y < existing.y + existing.width and y + W > existing.y and
            z < existing.z + existing.height and z + H > existing.z):
            adjacency_bonus += 50
            
        if ((abs(existing.y + existing.width - y) < 0.1 or abs(y + W - existing.y) < 0.1) and
            x < existing.x + existing.length and x + L > existing.x and
            z < existing.z + existing.height and z + H > existing.z):
            adjacency_bonus += 50
    
    return base_score - adjacency_bonus

def get_grid_positions(container: Container3D, L: float, W: float, H: float) -> List[Tuple[float, float, float]]:
    """Generate systematic grid positions as fallback"""
    positions = []
    step = min(L, W, H) / 2
    
    for z in range(0, int(container.height - H) + 1, int(step)):
        for y in range(0, int(container.width - W) + 1, int(step)):
            for x in range(0, int(container.length - L) + 1, int(step)):
                positions.append((x, y, z))
    
    return positions