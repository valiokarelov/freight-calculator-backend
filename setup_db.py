# setup_db.py
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

try:
    from sqlalchemy import create_engine
    from api.database_models import Base
    
    # Create database
    DATABASE_URL = "sqlite:///./cargo_equipment.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    
    # Add some basic test data
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    # Import and create a basic equipment entry
    from api.database_models import EquipmentCatalog
    
    # Check if any equipment exists
    existing = db.query(EquipmentCatalog).first()
    if not existing:
        # Create basic truck trailer for testing
        truck = EquipmentCatalog(
            name="53-truck",
            full_name="53' Truck Trailer",
            category="truck",
            sub_category="trailer",
            type_code="53-truck",
            length_cm=636 * 2.54,  # Convert inches to cm
            width_cm=102 * 2.54,
            height_cm=110 * 2.54,
            original_unit="in",
            max_payload_kg=26000,
            description="Standard 53-foot truck trailer",
            is_preset=True,
            is_active=True
        )
        db.add(truck)
        db.commit()
        print("Added basic equipment data!")
    
    db.close()
    
except Exception as e:
    print(f"Error: {e}")