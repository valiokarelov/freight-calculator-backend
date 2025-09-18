# File: algorithms/optimized_packing.py
from typing import List, Tuple, Optional
import math

from api.models import CargoItem3D, Container3D, PlacedItem3D

def volume_optimized_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Volume-optimized 3D packing - improved version of the basic algorithm
    """
    print(f"=== Volume-Optimized 3D Packing ===")
    print(f"Container: {container.length} x {container.width} x {container.height}")
    
    # Calculate container volume for early termination
    container_volume = container.length * container.width * container.height
    
    # Expand quantity to individual items
    individual_items = []
    total_item_volume = 0
    
    for item in items:
        item_volume = item.length * item.width * item.height
        total_item_volume += item_volume * item.quantity
        
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
    
    print(f"Total individual items: {len(individual_items)}")
    volume_ratio = total_item_volume / container_volume
    print(f"Volume ratio: {volume_ratio:.3f}")
    
    # Pre-filter items that are too large
    viable_items = []
    for item in individual_items:
        # Check all possible orientations
        orientations = [(item.length, item.width, item.height)]
        if not item.non_rotatable:
            orientations.extend([
                (item.width, item.length, item.height),
                (item.height, item.width, item.length)
            ])
        
        fits = any(
            l <= container.length and w <= container.width and h <= container.height
            for l, w, h in orientations
        )
        
        if fits:
            viable_items.append(item)
        else:
            print(f"Item {item.id} too large - skipping")
    
    print(f"Viable items after filtering: {len(viable_items)}")
    
    # Smart sorting: large items first, then by efficiency
    viable_items.sort(key=lambda x: (
        -(x.length * x.width * x.height),  # Volume descending
        min(x.length, x.width, x.height) / max(x.length, x.width, x.height),  # Prefer cube-like
        -x.weight  # Weight descending for stability
    ))
    
    # Optimized placement with space efficiency focus
    placed_items = []
    remaining_volume = container_volume
    
    for item in viable_items:
        # Early termination if remaining space is too small
        min_item_volume = item.length * item.width * item.height
        if remaining_volume < min_item_volume:
            print(f"Early termination: insufficient volume")
            break
        
        best_position = find_optimal_position(container, placed_items, item)
        
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
            remaining_volume -= min_item_volume
            
            if len(placed_items) % 20 == 0:
                print(f"Placed {len(placed_items)} items...")
    
    # Combine all items for return
    all_items = placed_items + [item for item in viable_items if not item.fitted]
    
    fitted_count = len(placed_items)
    total_count = len(all_items)
    efficiency = (container_volume - remaining_volume) / container_volume * 100
    
    print(f"Final: {fitted_count}/{total_count} items placed ({fitted_count/total_count*100:.1f}%)")
    print(f"Volume efficiency: {efficiency:.1f}%")
    
    return all_items

def find_optimal_position(container: Container3D, placed_items: List[PlacedItem3D], 
                         item: PlacedItem3D) -> Optional[dict]:
    """
    Find optimal position with focus on tight packing and space utilization
    """
    orientations = get_item_orientations(item)
    
    for orientation in orientations:
        L, W, H = orientation['length'], orientation['width'], orientation['height']
        
        # Skip if doesn't fit container
        if L > container.length or W > container.width or H > container.height:
            continue
        
        # Strategy 1: Try adjacent positions first (better packing)
        position = try_tight_placement(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2],
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
        
        # Strategy 2: Systematic grid search with fine resolution
        position = try_systematic_placement(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2],
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
    
    return None

def get_item_orientations(item: PlacedItem3D) -> List[dict]:
    """Get all valid orientations for an item"""
    if item.non_rotatable:
        return [{'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False}]
    
    # Try multiple orientations, starting with original
    orientations = [
        {'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False},
        {'length': item.width, 'width': item.length, 'height': item.height, 'rotated': True},
    ]
    
    # Add more orientations for non-cubic items
    if item.height != item.length and item.height != item.width:
        orientations.extend([
            {'length': item.height, 'width': item.width, 'height': item.length, 'rotated': True},
            {'length': item.width, 'width': item.height, 'height': item.length, 'rotated': True},
            {'length': item.length, 'width': item.height, 'height': item.width, 'rotated': True},
            {'length': item.height, 'width': item.length, 'height': item.width, 'rotated': True}
        ])
    
    return orientations

def try_tight_placement(container: Container3D, placed_items: List[PlacedItem3D], 
                       L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """
    Try placing adjacent to existing items for tight packing
    """
    if not placed_items:
        # First item goes at origin
        if is_valid_position(container, placed_items, (0, 0, 0), L, W, H, item):
            return (0, 0, 0)
        return None
    
    # Generate candidate positions adjacent to existing items
    candidates = set()
    
    # Sort existing items by volume (prioritize larger items for adjacency)
    sorted_existing = sorted(placed_items, key=lambda x: x.length * x.width * x.height, reverse=True)
    
    for existing in sorted_existing[:20]:  # Limit to avoid too many candidates
        
        # Right side
        pos = (existing.x + existing.length, existing.y, existing.z)
        if pos[0] + L <= container.length:
            candidates.add(pos)
        
        # Front side
        pos = (existing.x, existing.y + existing.width, existing.z)
        if pos[1] + W <= container.width:
            candidates.add(pos)
        
        # Top (if stacking allowed)
        if not existing.non_stackable and not item.non_stackable:
            pos = (existing.x, existing.y, existing.z + existing.height)
            if pos[2] + H <= container.height:
                candidates.add(pos)
        
        # Back-left corner
        pos = (existing.x - L, existing.y, existing.z)
        if pos[0] >= 0:
            candidates.add(pos)
        
        # Left-back corner
        pos = (existing.x, existing.y - W, existing.z)
        if pos[1] >= 0:
            candidates.add(pos)
    
    # Sort candidates by preference: lower positions first, then closer to origin
    sorted_candidates = sorted(candidates, key=lambda pos: (pos[2], pos[1], pos[0]))
    
    # Test each candidate position
    for pos in sorted_candidates:
        if is_valid_position(container, placed_items, pos, L, W, H, item):
            return pos
    
    return None

def try_systematic_placement(container: Container3D, placed_items: List[PlacedItem3D],
                           L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """
    Systematic grid search with fine resolution for gap filling
    """
    # Use smaller step size for better gap filling
    step_x = max(2, L / 4)  # Finer X resolution
    step_y = max(2, W / 4)  # Finer Y resolution  
    step_z = max(1, H / 4)  # Finest Z resolution for layering
    
    # Search layer by layer, preferring lower positions
    for z in range(0, int(container.height - H) + 1, int(step_z)):
        for y in range(0, int(container.width - W) + 1, int(step_y)):
            for x in range(0, int(container.length - L) + 1, int(step_x)):
                pos = (float(x), float(y), float(z))
                
                if is_valid_position(container, placed_items, pos, L, W, H, item):
                    return pos
    
    return None

def is_valid_position(container: Container3D, placed_items: List[PlacedItem3D], 
                     pos: Tuple[float, float, float], L: float, W: float, H: float, 
                     item: PlacedItem3D) -> bool:
    """
    Check if position is valid with comprehensive collision and support checking
    """
    x, y, z = pos
    
    # Container bounds check
    if x + L > container.length or y + W > container.width or z + H > container.height:
        return False
    
    # Collision detection
    for existing in placed_items:
        if (x < existing.x + existing.length and x + L > existing.x and
            y < existing.y + existing.width and y + W > existing.y and
            z < existing.z + existing.height and z + H > existing.z):
            return False
    
    # Support validation for elevated items
    if z > 0.1:  # Not on ground level
        if item.non_stackable:
            return False
        
        # Calculate support area
        support_area = 0
        required_support = L * W * 0.6  # Require 60% support
        
        for existing in placed_items:
            if existing.non_stackable:
                continue
            
            # Check if existing item is at the right level to provide support
            if abs(existing.z + existing.height - z) < 0.1:
                # Calculate overlap area
                overlap_x = max(0, min(x + L, existing.x + existing.length) - max(x, existing.x))
                overlap_y = max(0, min(y + W, existing.y + existing.width) - max(y, existing.y))
                
                if overlap_x > 0 and overlap_y > 0:
                    support_area += overlap_x * overlap_y
        
        if support_area < required_support:
            return False
    
    return True