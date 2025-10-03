#!/usr/bin/env python3
"""
Minimal test server for Farfalle intel endpoint
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from backend.intel.router import router as intel_router

app = FastAPI(title="Farfalle Intel Test")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include intel router
app.include_router(intel_router)

@app.get("/")
async def root():
    return {"message": "Farfalle Intel Test Server", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

