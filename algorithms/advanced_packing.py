# File: algorithms/advanced_packing.py - HYBRID VERSION
from typing import List, Tuple, Optional
import math

from api.models import CargoItem3D, Container3D, PlacedItem3D

def advanced_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Hybrid 3D bin packing - combines simple effectiveness with smart optimizations
    """
    print(f"=== Hybrid 3D Packing ===")
    print(f"Container: {container.length} x {container.width} x {container.height}")
    
    # Expand quantity to individual items
    individual_items = []
    for item in items:
        for i in range(item.quantity):
            individual_items.append(PlacedItem3D(
                id=f"{item.id}_{i+1}" if item.quantity > 1 else item.id,
                name=f"{item.name} #{i+1}" if item.quantity > 1 else item.name,
                length=item.length,
                width=item.width,
                height=item.height,
                weight=item.weight,
                quantity=1,
                non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable,
                x=0, y=0, z=0, 
                fitted=False, 
                rotated=False
            ))
    
    # Smart sorting: volume descending, aspect ratio ascending (prefer cubes), weight descending
    individual_items.sort(key=lambda x: (
        -(x.length * x.width * x.height),  # Largest items first
        max(x.length, x.width, x.height) / min(x.length, x.width, x.height),  # Prefer cube-like items
        -x.weight  # Heavier items first
    ))
    
    placed_items = []
    
    for item in individual_items:
        best_position = find_best_position_hybrid(container, placed_items, item)
        
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
    
    fitted_count = len(placed_items)
    total_count = len(individual_items)
    print(f"Final: {fitted_count}/{total_count} items placed ({fitted_count/total_count*100:.1f}%)")
    
    return individual_items

def find_best_position_hybrid(container: Container3D, placed_items: List[PlacedItem3D], item: PlacedItem3D) -> Optional[dict]:
    """
    Hybrid approach: Try adjacent positions first, then smart grid search
    """
    
    # Get possible orientations
    orientations = get_orientations_hybrid(item)
    
    for orientation in orientations:
        L, W, H = orientation['length'], orientation['width'], orientation['height']
        
        # Skip if doesn't fit
        if L > container.length or W > container.width or H > container.height:
            continue
        
        # Strategy 1: Try adjacent positions (more efficient packing)
        position = try_adjacent_placement(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2],
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
        
        # Strategy 2: Smart grid search (guaranteed to work if space exists)
        position = try_grid_placement(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2], 
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
    
    return None

def get_orientations_hybrid(item: PlacedItem3D) -> List[dict]:
    """Get orientations, trying original first"""
    if item.non_rotatable:
        return [{'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False}]
    
    # Try original orientation first, then rotated
    return [
        {'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False},
        {'length': item.width, 'width': item.length, 'height': item.height, 'rotated': True}
    ]

def try_adjacent_placement(container: Container3D, placed_items: List[PlacedItem3D], 
                          L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """Try placing adjacent to existing items for better packing efficiency"""
    
    if not placed_items:
        if is_valid_position_simple(container, placed_items, (0, 0, 0), L, W, H, item):
            return (0, 0, 0)
        return None
    
    # Generate adjacent positions
    candidate_positions = set()
    
    # Sort placed items by volume (prioritize larger items for better stability)
    sorted_placed = sorted(placed_items, key=lambda x: x.length * x.width * x.height, reverse=True)
    
    for existing in sorted_placed[:15]:  # Limit to top 15 items to avoid too many candidates
        
        # Right side
        if existing.x + existing.length + L <= container.length:
            candidate_positions.add((existing.x + existing.length, existing.y, existing.z))
        
        # Front side  
        if existing.y + existing.width + W <= container.width:
            candidate_positions.add((existing.x, existing.y + existing.width, existing.z))
        
        # Top (if stacking allowed)
        if not existing.non_stackable and not item.non_stackable and existing.z + existing.height + H <= container.height:
            candidate_positions.add((existing.x, existing.y, existing.z + existing.height))
    
    # Test positions in order of preference (lower first, then closer to origin)
    sorted_positions = sorted(candidate_positions, key=lambda pos: (pos[2], pos[1], pos[0]))
    
    for pos in sorted_positions:
        if is_valid_position_simple(container, placed_items, pos, L, W, H, item):
            return pos
    
    return None

def try_grid_placement(container: Container3D, placed_items: List[PlacedItem3D],
                      L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """Smart grid search with adaptive step size"""
    
    # Adaptive step size based on container and item dimensions
    step_x = max(10, min(L/2, container.length/15))
    step_y = max(10, min(W/2, container.width/15))  
    step_z = max(5, min(H/2, container.height/20))   # Finer Z resolution for better layering
    
    # Search with preference for lower positions
    for z in range(0, int(container.height - H) + 1, int(step_z)):
        for y in range(0, int(container.width - W) + 1, int(step_y)):
            for x in range(0, int(container.length - L) + 1, int(step_x)):
                pos = (float(x), float(y), float(z))
                
                if is_valid_position_simple(container, placed_items, pos, L, W, H, item):
                    return pos
    
    return None

def is_valid_position_simple(container: Container3D, placed_items: List[PlacedItem3D], 
                           pos: Tuple[float, float, float], L: float, W: float, H: float, 
                           item: PlacedItem3D) -> bool:
    """Simple but effective collision detection with basic support check"""
    x, y, z = pos
    
    # Container bounds check
    if x + L > container.length or y + W > container.width or z + H > container.height:
        return False
    
    # Collision check against all placed items
    for existing in placed_items:
        if (x < existing.x + existing.length and x + L > existing.x and
            y < existing.y + existing.width and y + W > existing.y and
            z < existing.z + existing.height and z + H > existing.z):
            return False
    
    # Basic support check for stacked items
    if z > 0.1:  # Not on ground level
        if item.non_stackable:
            return False
        
        # Find supporting area
        support_area = 0
        for existing in placed_items:
            # Check if existing item can provide support at our level
            if (existing.non_stackable or 
                abs(existing.z + existing.height - z) > 0.1):
                continue
            
            # Calculate overlap area
            overlap_x = max(0, min(x + L, existing.x + existing.length) - max(x, existing.x))
            overlap_y = max(0, min(y + W, existing.y + existing.width) - max(y, existing.y))
            
            if overlap_x > 0 and overlap_y > 0:
                support_area += overlap_x * overlap_y
        
        # Require at least 40% support area
        required_support = L * W * 0.4
        return support_area >= required_support
    
    return True