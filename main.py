from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.calculations import router as calc_router
from api.data_endpoints import router as data_router
import uvicorn
import os

# Create FastAPI instance
app = FastAPI(
    title="Freight Calculator API",
    description="Backend API for freight forwarding calculations",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(calc_router, prefix="/api/calculations", tags=["calculations"])
app.include_router(data_router, prefix="/api/data", tags=["data"])

@app.get("/")
def read_root():
    return {
        "message": "Freight Calculator API is running",
        "version": "1.0.0",
        "endpoints": {
            "calculations": "/api/calculations",
            "data": "/api/data",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "freight-calculator-api"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)