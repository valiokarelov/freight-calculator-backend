# File: algorithms/advanced_packing.py - DEBUG VERSION
from typing import List, Tuple, Optional, Set
import math

# Import the models - adjust path if needed based on your project structure
from api.models import CargoItem3D, Container3D, PlacedItem3D

def advanced_3d_packing(container: Container3D, items: List[CargoItem3D]) -> List[PlacedItem3D]:
    """
    Debug version with extensive logging
    """
    print(f"=== DEBUG: Starting 3D Packing ===")
    print(f"Container: {container.length} x {container.width} x {container.height}")
    print(f"Max weight: {container.max_weight}")
    print(f"Number of item types: {len(items)}")
    
    # Expand quantity to individual items
    individual_items = []
    for item in items:
        print(f"Item: {item.name} - {item.length}x{item.width}x{item.height}, qty: {item.quantity}")
        
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
    
    # Simple first-fit algorithm for debugging
    placed_items = []
    
    for item in individual_items:
        print(f"\nTrying to place: {item.name} ({item.length}x{item.width}x{item.height})")
        
        # Check if item fits in container at all
        if (item.length > container.length or 
            item.width > container.width or 
            item.height > container.height):
            print(f"  -> Too big for container!")
            continue
        
        # Try to place at origin first
        position_found = False
        
        # Simple grid search with larger steps
        step_size = 20  # 20cm steps
        
        for z in range(0, int(container.height - item.height) + 1, step_size):
            if position_found:
                break
            for y in range(0, int(container.width - item.width) + 1, step_size):
                if position_found:
                    break
                for x in range(0, int(container.length - item.length) + 1, step_size):
                    
                    # Check if position is valid
                    collision = False
                    
                    # Check against all placed items
                    for existing in placed_items:
                        if (x < existing.x + existing.length and x + item.length > existing.x and
                            y < existing.y + existing.width and y + item.width > existing.y and
                            z < existing.z + existing.height and z + item.height > existing.z):
                            collision = True
                            break
                    
                    if not collision:
                        # Place the item
                        item.x = float(x)
                        item.y = float(y)
                        item.z = float(z)
                        item.fitted = True
                        placed_items.append(item)
                        position_found = True
                        print(f"  -> Placed at ({x}, {y}, {z})")
                        break
        
        if not position_found:
            print(f"  -> Could not find position")
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total items: {len(individual_items)}")
    print(f"Placed items: {len(placed_items)}")
    print(f"Success rate: {len(placed_items)/len(individual_items)*100:.1f}%")
    
    return individual_items

# Keep the SpatialIndex class but don't use it for now
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