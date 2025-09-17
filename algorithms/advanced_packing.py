# File: algorithms/advanced_packing.py
from typing import List, Tuple, Optional, Set
import math

# Import the models - adjust path if needed based on your project structure
from api.models import CargoItem3D, Container3D, PlacedItem3D

class SpatialIndex:
    """Spatial grid for fast collision detection"""
    
    def __init__(self, container: Container3D, cell_size: float = 50.0):
        self.cell_size = cell_size
        self.grid = {}
        self.max_x = int(container.length / cell_size) + 1
        self.max_y = int(container.width / cell_size) + 1
        self.max_z = int(container.height / cell_size) + 1
    
    def _get_cells(self, x: float, y: float, z: float, L: float, W: float, H: float) -> Set[Tuple[int, int, int]]:
        """Get all grid cells that an item occupies"""
        min_x = int(x / self.cell_size)
        max_x = int((x + L) / self.cell_size)
        min_y = int(y / self.cell_size)
        max_y = int((y + W) / self.cell_size)
        min_z = int(z / self.cell_size)
        max_z = int((z + H) / self.cell_size)
        
        cells = set()
        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                for gz in range(min_z, max_z + 1):
                    cells.add((gx, gy, gz))
        return cells
    
    def add_item(self, item: PlacedItem3D):
        """Add item to spatial index"""
        cells = self._get_cells(item.x, item.y, item.z, item.length, item.width, item.height)
        for cell in cells:
            if cell not in self.grid:
                self.grid[cell] = []
            self.grid[cell].append(item)
    
    def get_potential_collisions(self, x: float, y: float, z: float, L: float, W: float, H: float) -> List[PlacedItem3D]:
        """Get items that might collide with given bounds"""
        potential_items = set()
        cells = self._get_cells(x, y, z, L, W, H)
        
        for cell in cells:
            if cell in self.grid:
                potential_items.update(self.grid[cell])
        
        return list(potential_items)

def advanced_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Optimized 3D bin packing with spatial indexing and smart search
    """
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
                quantity=1,  # Each individual item has quantity 1
                non_stackable=item.non_stackable,
                non_rotatable=item.non_rotatable,
                x=0, y=0, z=0, 
                fitted=False, 
                rotated=False
            ))
    
    # Smart sorting: volume, then aspect ratio, then weight
    individual_items.sort(key=lambda x: (
        -(x.length * x.width * x.height),  # Volume (descending)
        max(x.length, x.width, x.height) / min(x.length, x.width, x.height),  # Aspect ratio (ascending - prefer cubes)
        -x.weight  # Weight (descending)
    ))
    
    placed_items = []
    spatial_index = SpatialIndex(container)
    
    for item in individual_items:
        best_position = find_best_position_optimized(container, placed_items, item, spatial_index)
        
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
            spatial_index.add_item(item)
    
    return individual_items

def find_best_position_optimized(container: Container3D, placed_items: List[PlacedItem3D], 
                                item: PlacedItem3D, spatial_index: SpatialIndex) -> Optional[dict]:
    """
    Optimized position finding with early termination and smart search
    """
    orientations = get_orientations(item)
    candidates = []
    
    for orientation in orientations:
        L, W, H = orientation['length'], orientation['width'], orientation['height']
        
        # Skip if doesn't fit in container
        if L > container.length or W > container.width or H > container.height:
            continue
        
        # Try adjacent positions first (most efficient packing)
        adjacent_positions = get_adjacent_positions_optimized(container, placed_items, L, W, H)
        
        for pos in adjacent_positions[:10]:  # Limit adjacent positions to check
            if is_valid_position_optimized(container, pos, L, W, H, item, spatial_index):
                score = calculate_position_score_fast(pos, L, W, H, placed_items)
                candidates.append({
                    'x': pos[0], 'y': pos[1], 'z': pos[2],
                    'length': L, 'width': W, 'height': H,
                    'score': score, 'rotated': orientation.get('rotated', False)
                })
        
        # If we found good adjacent positions, use them
        if candidates:
            break
        
        # Fallback: smart grid search (much coarser)
        grid_positions = get_smart_grid_positions(container, L, W, H, max_positions=50)
        
        for pos in grid_positions:
            if is_valid_position_optimized(container, pos, L, W, H, item, spatial_index):
                score = calculate_position_score_fast(pos, L, W, H, placed_items)
                candidates.append({
                    'x': pos[0], 'y': pos[1], 'z': pos[2],
                    'length': L, 'width': W, 'height': H,
                    'score': score, 'rotated': orientation.get('rotated', False)
                })
                break  # Take first valid position from each orientation
    
    return min(candidates, key=lambda x: x['score']) if candidates else None

def get_orientations(item: PlacedItem3D) -> List[dict]:
    """Get possible orientations for an item"""
    if item.non_rotatable:
        return [{'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False}]
    
    # Try both orientations, but prefer original orientation
    orientations = [
        {'length': item.length, 'width': item.width, 'height': item.height, 'rotated': False},
        {'length': item.width, 'width': item.length, 'height': item.height, 'rotated': True},
    ]
    
    return orientations

def get_adjacent_positions_optimized(container: Container3D, placed_items: List[PlacedItem3D], 
                                   L: float, W: float, H: float) -> List[Tuple[float, float, float]]:
    """Generate positions adjacent to existing items with deduplication"""
    if not placed_items:
        return [(0, 0, 0)]
    
    positions = set()
    
    # Sort by volume to prioritize positions near larger items (better stability)
    sorted_items = sorted(placed_items, key=lambda x: x.length * x.width * x.height, reverse=True)
    
    for item in sorted_items[:20]:  # Limit to top 20 items to avoid too many positions
        # Right side
        if item.x + item.length + L <= container.length:
            positions.add((item.x + item.length, item.y, item.z))
        
        # Front side
        if item.y + item.width + W <= container.width:
            positions.add((item.x, item.y + item.width, item.z))
        
        # Top (if stacking allowed)
        if not item.non_stackable and item.z + item.height + H <= container.height:
            positions.add((item.x, item.y, item.z + item.height))
    
    # Sort positions by preference (lower first, then closer to origin)
    return sorted(list(positions), key=lambda pos: (pos[2], pos[1], pos[0]))

def get_smart_grid_positions(container: Container3D, L: float, W: float, H: float, 
                           max_positions: int = 50) -> List[Tuple[float, float, float]]:
    """Generate smart grid positions with adaptive step size"""
    positions = []
    
    # Adaptive step size based on item and container dimensions
    step_x = max(10.0, min(L, container.length / 10))
    step_y = max(10.0, min(W, container.width / 10))
    step_z = max(5.0, min(H, container.height / 10))  # Smaller z steps for better layering
    
    # Generate positions with priority order
    positions_added = 0
    
    for z in range(0, int(container.height - H) + 1, int(step_z)):
        if positions_added >= max_positions:
            break
        for y in range(0, int(container.width - W) + 1, int(step_y)):
            if positions_added >= max_positions:
                break
            for x in range(0, int(container.length - L) + 1, int(step_x)):
                if positions_added >= max_positions:
                    break
                positions.append((float(x), float(y), float(z)))
                positions_added += 1
    
    return positions

def is_valid_position_optimized(container: Container3D, pos: Tuple[float, float, float], 
                              L: float, W: float, H: float, item: PlacedItem3D,
                              spatial_index: SpatialIndex) -> bool:
    """Optimized collision detection using spatial indexing"""
    x, y, z = pos
    
    # Quick bounds check
    if x + L > container.length or y + W > container.width or z + H > container.height:
        return False
    
    # Fast collision detection using spatial index
    potential_collisions = spatial_index.get_potential_collisions(x, y, z, L, W, H)
    
    for existing in potential_collisions:
        if (x < existing.x + existing.length - 0.01 and x + L > existing.x + 0.01 and
            y < existing.y + existing.width - 0.01 and y + W > existing.y + 0.01 and
            z < existing.z + existing.height - 0.01 and z + H > existing.z + 0.01):
            return False
    
    # Support check (simplified for performance)
    if z > 0.1:  # Not on ground
        if item.non_stackable:
            return False
        
        # Quick support check - at least 50% support required
        support_area = 0
        required_support = L * W * 0.5  # Reduced from 70% for performance
        
        for existing in potential_collisions:
            if existing.non_stackable or abs(existing.z + existing.height - z) > 0.1:
                continue
            
            overlap_x = max(0, min(x + L, existing.x + existing.length) - max(x, existing.x))
            overlap_y = max(0, min(y + W, existing.y + existing.width) - max(y, existing.y))
            support_area += overlap_x * overlap_y
            
            if support_area >= required_support:  # Early termination
                break
        
        return support_area >= required_support
    
    return True

def calculate_position_score_fast(pos: Tuple[float, float, float], L: float, W: float, H: float,
                                placed_items: List[PlacedItem3D]) -> float:
    """Fast position scoring with simplified adjacency calculation"""
    x, y, z = pos
    
    # Base score: prefer lower positions and positions closer to origin
    base_score = z * 100 + y * 10 + x
    
    # Quick adjacency bonus (simplified calculation)
    adjacency_bonus = 0
    if placed_items:
        # Check only against nearest items for performance
        nearest_items = sorted(placed_items, key=lambda item: 
                             abs(item.x - x) + abs(item.y - y) + abs(item.z - z))[:5]
        
        for existing in nearest_items:
            # Simple distance-based adjacency bonus
            distance = abs(existing.x + existing.length - x) + abs(existing.y + existing.width - y)
            if distance < 1.0:  # Very close
                adjacency_bonus += 20
    
    return base_score - adjacency_bonus