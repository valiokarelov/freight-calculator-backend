import sqlite3
from datetime import datetime

# Air pallets data with full_name added
air_pallets_data = [
    {
        "name": "PMC/P6P - LD",
        "full_name": "PMC/P6P - LD Container",
        "category": "air-container",
        "length": 124.8,
        "width": 96.1,
        "height": 64,
        "type_code": "PMC-P6P-LD",
        "units": "in",
        "description": "PMC/P6P - LD Container"
    },
    {
        "name": "PMC/P6P - LD (Winged)",
        "full_name": "PMC/P6P - LD (Winged) Container", 
        "category": "air-container",
        "length": 164.2,
        "width": 96.1,
        "height": 64.2,
        "type_code": "PMC-P6P-LD-WINGED",
        "units": "in",
        "description": "PMC/P6P - LD (Winged) Container"
    },
    {
        "name": "PMC/P6P - Q6",
        "full_name": "PMC/P6P - Q6 Container",
        "category": "air-container", 
        "length": 124.8,
        "width": 96.1,
        "height": 96,
        "type_code": "PMC-P6P-Q6",
        "units": "in",
        "description": "PMC/P6P - Q6 Container"
    },
    {
        "name": "PAG/P1P - LD-7",
        "full_name": "PAG/P1P - LD-7 Container",
        "category": "air-container",
        "length": 88.2,
        "width": 124.8,
        "height": 64.2,
        "type_code": "PAG-P1P-LD7",
        "units": "in",
        "description": "PAG/P1P - LD-7 Container"
    },
    {
        "name": "LD-3 / AKE",
        "full_name": "LD-3 / AKE Container",
        "category": "air-container",
        "length": 75.6,
        "width": 57.1,
        "height": 63.8,
        "type_code": "LD3-AKE",
        "units": "in",
        "description": "LD-3 / AKE Container"
    }
]

def import_air_pallets():
    conn = sqlite3.connect('cargo_equipment.db')
    cursor = conn.cursor()
    
    imported_count = 0
    skipped_count = 0
    
    for item in air_pallets_data:
        cursor.execute('SELECT COUNT(*) FROM equipment_catalog WHERE type_code = ?', (item['type_code'],))
        if cursor.fetchone()[0] > 0:
            print(f"Skipping {item['name']} - already exists")
            skipped_count += 1
            continue
        
        length_cm = item['length'] * 2.54
        width_cm = item['width'] * 2.54
        height_cm = item['height'] * 2.54
        
        try:
            cursor.execute('''
                INSERT INTO equipment_catalog 
                (name, full_name, category, length_cm, width_cm, height_cm, type_code, original_unit, description, is_preset, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['name'],
                item['full_name'],  # Added this field
                item['category'],
                length_cm,
                width_cm,
                height_cm,
                item['type_code'],
                item['units'],
                item['description'],
                True,
                True,
                datetime.now(),
                datetime.now()
            ))
            imported_count += 1
            print(f"Added: {item['name']}")
            
        except sqlite3.Error as e:
            print(f"Error inserting {item['name']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nImport complete!")
    print(f"Imported: {imported_count} items")
    print(f"Skipped: {skipped_count} items")

if __name__ == "__main__":
    import_air_pallets()