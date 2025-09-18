# File: algorithms/optimized_packing.py
from typing import List, Tuple, Optional
import math

from api.models import CargoItem3D, Container3D, PlacedItem3D

def volume_optimized_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Volume-optimized 3D packing with intelligent pre-filtering and priority sorting
    """
    print(f"=== Volume-Optimized 3D Packing ===")
    print(f"Container: {container.length} x {container.width} x {container.height}")
    
    # Calculate container volume and remaining space tracking
    container_volume = container.length * container.width * container.height
    remaining_volume = container_volume
    
    # Expand quantity to individual items
    individual_items = []
    for item in items:
        item_volume = item.length * item.width * item.height
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
                rotated=False,
                _volume=item_volume  # Cache volume for efficiency
            ))
    
    print(f"Total individual items: {len(individual_items)}")
    
    # STEP 1: Volume-based pre-filtering
    viable_items, oversized_items = volume_prefilter(individual_items, container, container_volume)
    print(f"After volume filtering: {len(viable_items)} viable, {len(oversized_items)} oversized")
    
    # STEP 2: Smart priority sorting
    viable_items = smart_priority_sort(viable_items)
    
    # STEP 3: Optimized placement with volume tracking
    placed_items = []
    total_placed_volume = 0
    
    for item in viable_items:
        # Early termination if remaining volume is insufficient
        if remaining_volume < item._volume * 0.4:  # Account for packing efficiency
            print(f"Early termination: insufficient volume remaining")
            break
        
        best_position = find_best_position_optimized(container, placed_items, item, remaining_volume)
        
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
            total_placed_volume += item._volume
            remaining_volume -= item._volume
            
            # Progress logging for large batches
            if len(placed_items) % 50 == 0:
                print(f"Placed {len(placed_items)} items, {remaining_volume/container_volume*100:.1f}% volume remaining")
    
    # Combine placed and unplaced items
    all_items = placed_items + [item for item in viable_items if not item.fitted] + oversized_items
    
    fitted_count = len(placed_items)
    total_count = len(all_items)
    volume_efficiency = (total_placed_volume / container_volume) * 100
    
    print(f"Final: {fitted_count}/{total_count} items placed ({fitted_count/total_count*100:.1f}%)")
    print(f"Volume efficiency: {volume_efficiency:.1f}%")
    
    return all_items

def volume_prefilter(items: List[PlacedItem3D], container: Container3D, container_volume: float) -> Tuple[List[PlacedItem3D], List[PlacedItem3D]]:
    """
    Pre-filter items based on volume and dimensional constraints
    """
    viable_items = []
    oversized_items = []
    
    # Calculate total requested volume
    total_item_volume = sum(item._volume for item in items)
    volume_ratio = total_item_volume / container_volume
    
    print(f"Volume ratio: {volume_ratio:.2f} (total items volume / container volume)")
    
    for item in items:
        # Check dimensional constraints (with rotation if allowed)
        dimensions = [(item.length, item.width, item.height)]
        if not item.non_rotatable:
            dimensions.extend([
                (item.width, item.length, item.height),
                (item.height, item.width, item.length),
                (item.width, item.height, item.length),
                (item.length, item.height, item.width),
                (item.height, item.length, item.width)
            ])
        
        fits_dimensionally = any(
            l <= container.length and w <= container.width and h <= container.height
            for l, w, h in dimensions
        )
        
        if fits_dimensionally:
            viable_items.append(item)
        else:
            item.fitted = False
            oversized_items.append(item)
    
    # If volume ratio is very high (>0.95), be more selective
    if volume_ratio > 0.95:
        print("High volume ratio detected, applying stricter filtering")
        viable_items = apply_strict_volume_filter(viable_items, container_volume, volume_ratio)
    
    return viable_items, oversized_items

def apply_strict_volume_filter(items: List[PlacedItem3D], container_volume: float, volume_ratio: float) -> List[PlacedItem3D]:
    """
    Apply stricter filtering when volume ratio is very high
    """
    # Sort by volume efficiency (volume/surface_area ratio) - prefer compact items
    items_with_efficiency = []
    for item in items:
        surface_area = 2 * (item.length * item.width + item.length * item.height + item.width * item.height)
        efficiency = item._volume / surface_area if surface_area > 0 else 0
        items_with_efficiency.append((item, efficiency))
    
    items_with_efficiency.sort(key=lambda x: x[1], reverse=True)
    
    # Take only items that fit within realistic packing efficiency
    target_volume = container_volume * 0.85  # Assume 85% max packing efficiency
    selected_items = []
    current_volume = 0
    
    for item, efficiency in items_with_efficiency:
        if current_volume + item._volume <= target_volume:
            selected_items.append(item)
            current_volume += item._volume
    
    print(f"Strict filtering: {len(selected_items)}/{len(items)} items selected")
    return selected_items

def smart_priority_sort(items: List[PlacedItem3D]) -> List[PlacedItem3D]:
    """
    Smart sorting: Large items first, then optimized for space efficiency
    """
    # Separate into large and small items
    volume_threshold = sorted([item._volume for item in items], reverse=True)[min(len(items)//4, 20)] if items else 0
    
    large_items = [item for item in items if item._volume >= volume_threshold]
    small_items = [item for item in items if item._volume < volume_threshold]
    
    # Sort large items by volume (largest first)
    large_items.sort(key=lambda x: -x._volume)
    
    # Sort small items by efficiency metrics
    small_items.sort(key=lambda x: (
        -x._volume,  # Volume descending
        min(x.length, x.width, x.height) / max(x.length, x.width, x.height),  # Prefer cube-like shapes
        -x.weight  # Weight descending for stability
    ))
    
    print(f"Priority sort: {len(large_items)} large items, {len(small_items)} small items")
    return large_items + small_items

def find_best_position_optimized(container: Container3D, placed_items: List[PlacedItem3D], 
                                item: PlacedItem3D, remaining_volume: float) -> Optional[dict]:
    """
    Optimized position finding with volume awareness
    """
    orientations = get_orientations_hybrid(item)
    
    for orientation in orientations:
        L, W, H = orientation['length'], orientation['width'], orientation['height']
        
        # Skip if doesn't fit
        if L > container.length or W > container.width or H > container.height:
            continue
        
        # Strategy 1: Adjacent placement (most efficient)
        position = try_adjacent_placement_optimized(container, placed_items, L, W, H, item)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2],
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
        
        # Strategy 2: Grid search with adaptive density based on remaining volume
        grid_density = calculate_adaptive_grid_density(remaining_volume, container, L, W, H)
        position = try_adaptive_grid_placement(container, placed_items, L, W, H, item, grid_density)
        if position:
            return {
                'x': position[0], 'y': position[1], 'z': position[2],
                'length': L, 'width': W, 'height': H,
                'rotated': orientation.get('rotated', False)
            }
    
    return None

def try_adjacent_placement_optimized(container: Container3D, placed_items: List[PlacedItem3D], 
                                   L: float, W: float, H: float, item: PlacedItem3D) -> Optional[Tuple[float, float, float]]:
    """
    Optimized adjacent placement with better candidate generation
    """
    if not placed_items:
        if is_valid_position_simple(container, placed_items, (0, 0, 0), L, W, H, item):
            return (0, 0, 0)
        return None
    
    # Generate fewer, better candidates
    candidate_positions = set()
    
    # Only consider the most recently placed items for adjacency (better locality)
    recent_items = placed_items[-min(10, len(placed_items)):]
    
    for existing in recent_items:
        # Standard adjacent positions
        positions = [
            (existing.x + existing.length, existing.y, existing.z),  # Right
            (existing.x, existing.y + existing.width, existing.z),   # Front
        ]
        
        # Top position only if stacking makes sense
        if (not existing.non_stackable and not item.non_stackable and 
            existing.z + existing.height + H <= container.height):
            positions.append((existing.x, existing.y, existing.z + existing.height))
        
        for pos in positions:
            if (pos[0] + L <= container.length and 
                pos[1] + W <= container.width and 
                pos[2] + H <= container.height):
                candidate_positions.add(pos)
    
    # Test positions in priority order
    sorted_positions = sorted(candidate_positions, key=lambda pos: (pos[2], pos[1], pos[0]))
    
    for pos in sorted_positions:
        if is_valid_position_simple(container, placed_items, pos, L, W, H, item):
            return pos
    
    return None

def calculate_adaptive_grid_density(remaining_volume: float, container: Container3D, 
                                  L: float, W: float, H: float) -> dict:
    """
    Calculate adaptive grid density based on remaining volume and item size
    """
    container_volume = container.length * container.width * container.height
    volume_ratio = remaining_volume / container_volume
    
    # Adaptive step size: finer grid when volume is scarce
    if volume_ratio > 0.5:
        # Plenty of space - use coarser grid
        step_factor = 0.5
    elif volume_ratio > 0.2:
        # Moderate space - medium grid
        step_factor = 0.3
    else:
        # Tight space - finer grid
        step_factor = 0.2
    
    return {
        'step_x': max(5, L * step_factor),
        'step_y': max(5, W * step_factor),
        'step_z': max(3, H * step_factor)
    }

def try_adaptive_grid_placement(container: Container3D, placed_items: List[PlacedItem3D],
                               L: float, W: float, H: float, item: PlacedItem3D, 
                               grid_density: dict) -> Optional[Tuple[float, float, float]]:
    """
    Grid search with adaptive density
    """
    step_x = grid_density['step_x']
    step_y = grid_density['step_y'] 
    step_z = grid_density['step_z']
    
    # Limit search iterations to prevent hanging
    max_iterations = 1000
    iteration_count = 0
    
    for z in range(0, int(container.height - H) + 1, int(step_z)):
        for y in range(0, int(container.width - W) + 1, int(step_y)):
            for x in range(0, int(container.length - L) + 1, int(step_x)):
                iteration_count += 1
                if iteration_count > max_iterations:
                    print(f"Grid search iteration limit reached for item {item.id}")
                    return None
                
                pos = (float(x), float(y), float(z))
                if is_valid_position_simple(container, placed_items, pos, L, W, H, item):
                    return pos
    
    return None

def get_orientations_hybrid(item: PlacedItem3D) -> List[dict]:
    """Get orientations, trying original first"""
    if item.non_rotatable:
        return [{'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False}]
    
    # Try original orientation first, then most promising rotations
    return [
        {'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False},
        {'length': item.width, 'width': item.length, 'height': item.height, 'rotated': True},
        # Add more orientations only for significantly non-cubic items
        {'length': item.height, 'width': item.width, 'height': item.length, 'rotated': True} 
        if max(item.length, item.width, item.height) / min(item.length, item.width, item.height) > 2 else None
    ]

def is_valid_position_simple(container: Container3D, placed_items: List[PlacedItem3D], 
                           pos: Tuple[float, float, float], L: float, W: float, H: float, 
                           item: PlacedItem3D) -> bool:
    """
    Optimized collision detection with early termination
    """
    x, y, z = pos
    
    # Container bounds check
    if x + L > container.length or y + W > container.width or z + H > container.height:
        return False
    
    # Collision check with spatial optimization
    for existing in placed_items:
        # Quick distance check before detailed collision
        if (abs(existing.x - x) < existing.length + L and
            abs(existing.y - y) < existing.width + W and
            abs(existing.z - z) < existing.height + H):
            
            # Detailed collision check
            if (x < existing.x + existing.length and x + L > existing.x and
                y < existing.y + existing.width and y + W > existing.y and
                z < existing.z + existing.height and z + H > existing.z):
                return False
    
    # Simplified support check for stacked items
    if z > 0.1:  # Not on ground level
        if item.non_stackable:
            return False
        
        # Quick support validation - require 50% support area
        support_area = 0
        required_support = L * W * 0.5
        
        for existing in placed_items:
            if (existing.non_stackable or 
                abs(existing.z + existing.height - z) > 0.1):
                continue
            
            overlap_x = max(0, min(x + L, existing.x + existing.length) - max(x, existing.x))
            overlap_y = max(0, min(y + W, existing.y + existing.width) - max(y, existing.y))
            
            if overlap_x > 0 and overlap_y > 0:
                support_area += overlap_x * overlap_y
                if support_area >= required_support:  # Early termination
                    break
        
        return support_area >= required_support
    
    return True