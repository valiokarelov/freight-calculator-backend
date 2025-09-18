# File: algorithms/advanced_packing.py - IMPROVED VERSION
from typing import List, Tuple, Optional
import math

from api.models import CargoItem3D, Container3D, PlacedItem3D

def advanced_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Improved 3D bin packing with better space utilization
    """
    print(f"=== Improved 3D Packing ===")
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
    
    # Enhanced sorting: volume descending, then efficiency metrics
    individual_items.sort(key=lambda x: (
        -(x.length * x.width * x.height),  # Volume descending
        min(x.length, x.width, x.height) / max(x.length, x.width, x.height),  # Prefer cube-like
        -x.weight  # Weight descending for stability
    ))
    
    placed_items = []
    
    for item in individual_items:
        best_position = find_best_position_improved(container, placed_items, item)
        
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
            
            # Progress logging
            if len(placed_items) % 10 == 0:
                print(f"Placed {len(placed_items)} items...")
    
    fitted_count = len(placed_items)
    total_count = len(individual_items)
    efficiency = (fitted_count/total_count*100) if total_count > 0 else 0
    print(f"Final: {fitted_count}/{total_count} items placed ({efficiency:.1f}%)")
    
    return individual_items

def find_best_position_improved(container: Container3D, placed_items: List[PlacedItem3D], item: PlacedItem3D) -> Optional[dict]:
    """
    Improved position finding with multiple strategies and better orientations
    """
    
    # Get all possible orientations (more than before)
    orientations = get_orientations_improved(item)
    
    for orientation in orientations:
        L, W, H = orientation['length'], orientation['width'], orientation['height']
        
        # Skip if doesn't fit container
        if L > container.length or W > container.width or H > container.height:
            continue
        
        # Strategy 1: Corner placement (most space-efficient)
        position = try_corner_placement(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2],
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
        
        # Strategy 2: Adjacent placement (good packing density)
        position = try_adjacent_placement_improved(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2],
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
        
        # Strategy 3: Fine grid search (fills gaps)
        position = try_fine_grid_placement(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2], 
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
    
    return None

def get_orientations_improved(item: PlacedItem3D) -> List[dict]:
    """Get more orientations for better fitting"""
    if item.non_rotatable:
        return [{'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False}]
    
    # Try more orientations for better space utilization
    orientations = [
        {'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False},
        {'length': item.width, 'width': item.length, 'height': item.height, 'rotated': True},
    ]
    
    # Add vertical orientations if item is not cube-like
    dims = [item.length, item.width, item.height]
    if len(set(dims)) > 1:  # Not all dimensions are the same
        orientations.extend([
            {'length': item.height, 'width': item.width, 'height': item.length, 'rotated': True},
            {'length': item.width, 'width': item.height, 'height': item.length, 'rotated': True},
        ])
    
    return orientations

def try_corner_placement(container: Container3D, placed_items: List[PlacedItem3D], 
                        L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """
    Try placing at corners of existing items for maximum space efficiency
    """
    if not placed_items:
        if is_valid_position_improved(container, placed_items, (0, 0, 0), L, W, H, item):
            return (0, 0, 0)
        return None
    
    # Generate corner positions
    corners = set()
    
    for existing in placed_items:
        # Try corners of existing items
        potential_corners = [
            # Ground level corners
            (existing.x + existing.length, existing.y, existing.z),
            (existing.x, existing.y + existing.width, existing.z),
            (existing.x + existing.length, existing.y + existing.width, existing.z),
            # Top level corners (if stacking allowed)
        ]
        
        if not existing.non_stackable and not item.non_stackable:
            potential_corners.extend([
                (existing.x, existing.y, existing.z + existing.height),
                (existing.x + existing.length, existing.y, existing.z + existing.height),
                (existing.x, existing.y + existing.width, existing.z + existing.height),
                (existing.x + existing.length, existing.y + existing.width, existing.z + existing.height),
            ])
        
        for corner in potential_corners:
            if (corner[0] + L <= container.length and 
                corner[1] + W <= container.width and 
                corner[2] + H <= container.height):
                corners.add(corner)
    
    # Sort corners by preference: lower positions first, then closer to walls
    sorted_corners = sorted(corners, key=lambda pos: (pos[2], pos[1], pos[0]))
    
    for pos in sorted_corners:
        if is_valid_position_improved(container, placed_items, pos, L, W, H, item):
            return pos
    
    return None

def try_adjacent_placement_improved(container: Container3D, placed_items: List[PlacedItem3D], 
                                   L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """
    Improved adjacent placement with better candidate generation
    """
    candidate_positions = set()
    
    # Sort by volume and recency for better adjacency choices
    recent_items = sorted(placed_items, key=lambda x: x.length * x.width * x.height, reverse=True)[:20]
    
    for existing in recent_items:
        
        # Right side placement
        if existing.x + existing.length + L <= container.length:
            candidate_positions.add((existing.x + existing.length, existing.y, existing.z))
        
        # Front side placement
        if existing.y + existing.width + W <= container.width:
            candidate_positions.add((existing.x, existing.y + existing.width, existing.z))
        
        # Top placement (with stacking rules)
        if (not existing.non_stackable and not item.non_stackable and 
            existing.z + existing.height + H <= container.height):
            candidate_positions.add((existing.x, existing.y, existing.z + existing.height))
        
        # Back-left placement (for gap filling)
        if existing.x >= L:
            candidate_positions.add((existing.x - L, existing.y, existing.z))
        
        # Left-back placement (for gap filling)
        if existing.y >= W:
            candidate_positions.add((existing.x, existing.y - W, existing.z))
    
    # Sort by preference: lower positions first, then closer to origin
    sorted_positions = sorted(candidate_positions, key=lambda pos: (pos[2], pos[1], pos[0]))
    
    for pos in sorted_positions:
        if is_valid_position_improved(container, placed_items, pos, L, W, H, item):
            return pos
    
    return None

def try_fine_grid_placement(container: Container3D, placed_items: List[PlacedItem3D],
                           L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """
    Fine-resolution grid search for gap filling
    """
    # Use finer step size for better gap detection
    step_x = max(3, min(L/3, container.length/20))  # Finer resolution
    step_y = max(3, min(W/3, container.width/20))   
    step_z = max(2, min(H/3, container.height/25))  # Even finer Z resolution
    
    # Limit iterations to prevent excessive computation
    max_iterations = 800
    iteration_count = 0
    
    # Search layer by layer with fine resolution
    for z in range(0, int(container.height - H) + 1, int(step_z)):
        for y in range(0, int(container.width - W) + 1, int(step_y)):
            for x in range(0, int(container.length - L) + 1, int(step_x)):
                iteration_count += 1
                if iteration_count > max_iterations:
                    print(f"Grid search limit reached for item {item.id}")
                    return None
                
                pos = (float(x), float(y), float(z))
                if is_valid_position_improved(container, placed_items, pos, L, W, H, item):
                    return pos
    
    return None

def is_valid_position_improved(container: Container3D, placed_items: List[PlacedItem3D], 
                              pos: Tuple[float, float, float], L: float, W: float, H: float, 
                              item: PlacedItem3D) -> bool:
    """
    Improved position validation with better support checking
    """
    x, y, z = pos
    
    # Container bounds check
    if x + L > container.length or y + W > container.width or z + H > container.height:
        return False
    
    # Collision detection with early termination
    for existing in placed_items:
        if (x < existing.x + existing.length and x + L > existing.x and
            y < existing.y + existing.width and y + W > existing.y and
            z < existing.z + existing.height and z + H > existing.z):
            return False
    
    # Enhanced support check for stacked items
    if z > 0.1:  # Not on ground level
        if item.non_stackable:
            return False
        
        # Calculate required support area
        support_area = 0
        required_support = L * W * 0.5  # Require 50% support area
        
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
                    # Early termination if we have enough support
                    if support_area >= required_support:
                        break
        
        return support_area >= required_support
    
    return True