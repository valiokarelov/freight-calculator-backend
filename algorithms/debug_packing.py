# File: algorithms/debug_packing.py
from typing import List, Tuple, Optional
import math

from api.models import CargoItem3D, Container3D, PlacedItem3D

def debug_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Debug version with extensive logging to identify issues
    """
    print(f"\n=== DEBUG 3D PACKING ===")
    print(f"Container: {container.length} x {container.width} x {container.height} cm")
    print(f"Container volume: {container.length * container.width * container.height:.2f} cm³")
    
    # Expand quantity to individual items
    individual_items = []
    total_item_volume = 0
    
    for item_idx, item in enumerate(items):
        print(f"\nProcessing item {item_idx}: {item.name}")
        print(f"  Dimensions: {item.length} x {item.width} x {item.height} cm")
        print(f"  Quantity: {item.quantity}")
        print(f"  Weight: {item.weight} kg")
        print(f"  Non-stackable: {item.non_stackable}")
        print(f"  Non-rotatable: {item.non_rotatable}")
        
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
    
    print(f"\nTotal individual items created: {len(individual_items)}")
    print(f"Total item volume: {total_item_volume:.2f} cm³")
    print(f"Container volume: {container.length * container.width * container.height:.2f} cm³")
    volume_ratio = total_item_volume / (container.length * container.width * container.height)
    print(f"Volume ratio: {volume_ratio:.3f}")
    
    # Simple dimensional check first
    viable_items = []
    oversized_items = []
    
    for item in individual_items:
        print(f"\nChecking item: {item.id}")
        print(f"  Item dims: {item.length} x {item.width} x {item.height}")
        
        # Check if item fits in any orientation
        orientations = [
            (item.length, item.width, item.height),
            (item.width, item.length, item.height) if not item.non_rotatable else None,
            (item.height, item.width, item.length) if not item.non_rotatable else None,
            (item.width, item.height, item.length) if not item.non_rotatable else None,
            (item.length, item.height, item.width) if not item.non_rotatable else None,
            (item.height, item.length, item.width) if not item.non_rotatable else None
        ]
        
        # Remove None orientations
        orientations = [o for o in orientations if o is not None]
        
        fits = False
        for l, w, h in orientations:
            if l <= container.length and w <= container.width and h <= container.height:
                fits = True
                print(f"  ✓ Fits in orientation: {l} x {w} x {h}")
                break
        
        if fits:
            viable_items.append(item)
        else:
            print(f"  ✗ Does not fit in any orientation")
            oversized_items.append(item)
    
    print(f"\nAfter dimensional check:")
    print(f"  Viable items: {len(viable_items)}")
    print(f"  Oversized items: {len(oversized_items)}")
    
    if not viable_items:
        print("No viable items found - all items are oversized!")
        return individual_items
    
    # Sort viable items by volume (largest first)
    viable_items.sort(key=lambda x: x.length * x.width * x.height, reverse=True)
    
    # Simple placement algorithm
    placed_items = []
    
    for item_idx, item in enumerate(viable_items):
        print(f"\nTrying to place item {item_idx + 1}/{len(viable_items)}: {item.id}")
        
        best_position = find_simple_position(container, placed_items, item)
        
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
            print(f"  ✓ Placed at ({item.x}, {item.y}, {item.z})")
            print(f"  Final dims: {item.length} x {item.width} x {item.height}")
        else:
            print(f"  ✗ Could not find position")
    
    # Combine all items for return
    all_items = placed_items + [item for item in viable_items if not item.fitted] + oversized_items
    
    fitted_count = len(placed_items)
    total_count = len(all_items)
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Placed: {fitted_count}/{total_count} items ({fitted_count/total_count*100:.1f}%)")
    print(f"Fitted items: {[item.id for item in placed_items]}")
    print(f"Unfitted items: {[item.id for item in all_items if not item.fitted]}")
    
    return all_items

def find_simple_position(container: Container3D, placed_items: List[PlacedItem3D], 
                        item: PlacedItem3D) -> Optional[dict]:
    """
    Simple position finding with detailed logging
    """
    print(f"    Finding position for {item.id}")
    
    # Get orientations
    orientations = [
        {'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False}
    ]
    
    if not item.non_rotatable:
        orientations.append({
            'length': item.width, 'width': item.length, 'height': item.height, 'rotated': True
        })
    
    print(f"    Trying {len(orientations)} orientations")
    
    for orient_idx, orientation in enumerate(orientations):
        L, W, H = orientation['length'], orientation['width'], orientation['height']
        print(f"    Orientation {orient_idx + 1}: {L} x {W} x {H}")
        
        # Skip if doesn't fit container
        if L > container.length or W > container.width or H > container.height:
            print(f"      ✗ Too big for container")
            continue
        
        # Try simple positions
        positions_to_try = [(0, 0, 0)]  # Start with origin
        
        # Add positions adjacent to existing items
        for existing in placed_items[-5:]:  # Only last 5 items
            positions_to_try.extend([
                (existing.x + existing.length, existing.y, existing.z),  # Right
                (existing.x, existing.y + existing.width, existing.z),   # Front
                (existing.x, existing.y, existing.z + existing.height) if not existing.non_stackable else None  # Top
            ])
        
        # Remove None and out-of-bounds positions
        valid_positions = []
        for pos in positions_to_try:
            if pos is None:
                continue
            x, y, z = pos
            if (x + L <= container.length and 
                y + W <= container.width and 
                z + H <= container.height):
                valid_positions.append(pos)
        
        print(f"      Trying {len(valid_positions)} positions")
        
        for pos_idx, pos in enumerate(valid_positions):
            x, y, z = pos
            print(f"        Position {pos_idx + 1}: ({x}, {y}, {z})")
            
            if is_position_valid_debug(container, placed_items, pos, L, W, H, item):
                print(f"        ✓ Valid position found!")
                return {
                    'x': x, 'y': y, 'z': z,
                    'length': L, 'width': W, 'height': H,
                    'rotated': orientation.get('rotated', False)
                }
            else:
                print(f"        ✗ Position invalid")
    
    print(f"    No valid position found for {item.id}")
    return None

def is_position_valid_debug(container: Container3D, placed_items: List[PlacedItem3D], 
                           pos: Tuple[float, float, float], L: float, W: float, H: float, 
                           item: PlacedItem3D) -> bool:
    """
    Position validation with debug logging
    """
    x, y, z = pos
    
    # Container bounds check
    if x + L > container.length or y + W > container.width or z + H > container.height:
        print(f"          Bounds check failed")
        return False
    
    # Collision check
    for existing in placed_items:
        if (x < existing.x + existing.length and x + L > existing.x and
            y < existing.y + existing.width and y + W > existing.y and
            z < existing.z + existing.height and z + H > existing.z):
            print(f"          Collision with {existing.id}")
            return False
    
    # Support check for elevated items
    if z > 0.1:  # Not on ground
        if item.non_stackable:
            print(f"          Item is non-stackable but not on ground")
            return False
        
        support_area = 0
        for existing in placed_items:
            if existing.non_stackable:
                continue
            
            if abs(existing.z + existing.height - z) < 0.1:
                overlap_x = max(0, min(x + L, existing.x + existing.length) - max(x, existing.x))
                overlap_y = max(0, min(y + W, existing.y + existing.width) - max(y, existing.y))
                
                if overlap_x > 0 and overlap_y > 0:
                    support_area += overlap_x * overlap_y
        
        required_support = L * W * 0.5
        if support_area < required_support:
            print(f"          Insufficient support: {support_area:.1f} < {required_support:.1f}")
            return False
    
    return True