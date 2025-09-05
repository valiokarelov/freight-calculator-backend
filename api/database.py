# File: backend/api/database.py
# Simple database configuration to fix import errors

from typing import Generator, Any, Union
import os
SQLALCHEMY_AVAILABLE = True  # Since we have the models file

# Import FastAPI HTTPException
try:
    from fastapi import HTTPException
except ImportError:
    # Fallback if FastAPI not available
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

# Check if SQLAlchemy is available
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    print("SQLAlchemy not installed. Database features will be limited.")
    SQLALCHEMY_AVAILABLE = False
    # Create a dummy Session class for type hints
    class Session:
        pass

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cargo_equipment.db")

# Type alias for database session
DatabaseSession = Union[Session, Any]

if SQLALCHEMY_AVAILABLE:
    # Create database engine
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def get_db() -> Generator[DatabaseSession, None, None]:
        """Dependency to get database session"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_tables():
        """Create all database tables"""
        if SQLALCHEMY_AVAILABLE:
            try:
                from api.database_models import Base
                Base.metadata.create_all(bind=engine)
                print("Database tables created successfully!")
            except ImportError as e:
                print(f"Database models not found: {e}")
            except Exception as e:
                print(f"Error creating tables: {e}")
        else:
            print("SQLAlchemy not available. Cannot create database tables.")
    
    def check_database_connection():
        """Check if database is accessible"""
        try:
            with engine.connect() as connection:
                result = connection.execute("SELECT 1")
                print("✅ Database connection successful!")
                return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

else:
    # Fallback implementations when SQLAlchemy is not available
    engine = None
    SessionLocal = None
    
    def get_db() -> Generator[DatabaseSession, None, None]:
        """Fallback database dependency - raises error"""
        raise HTTPException(
            status_code=503, 
            detail="Database not configured. Please install SQLAlchemy: pip install sqlalchemy"
        )
        yield  # This will never execute but satisfies the generator requirement
    
    def create_tables():
        """Fallback table creation"""
        print("⚠️ SQLAlchemy not available. Cannot create database tables.")
        print("To use database features, install SQLAlchemy: pip install sqlalchemy")
    
    def check_database_connection():
        """Fallback connection check"""
        print("⚠️ SQLAlchemy not available. Cannot check database connection.")
        return False

# Export what's needed
__all__ = ["get_db", "create_tables", "check_database_connection", "SQLALCHEMY_AVAILABLE"]