#!/usr/bin/env python3
"""
Simple Voice MVP Server
Minimal FastAPI server for testing voice functionality
"""

import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
load_dotenv()

# Import CRM tools
try:
    from crm.tools import initiate_voice_call, get_call_status, get_voice_dashboard_data, call_with_context
    print("✅ CRM tools imported successfully")
except ImportError as e:
    print(f"❌ Failed to import CRM tools: {e}")
    sys.exit(1)

# Create FastAPI app
app = FastAPI(
    title="Voice MVP Server",
    description="Simple server for Voice MVP testing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Voice MVP Server is running! 🎉"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-mvp",
        "version": "1.0.0"
    }

@app.post("/voice/initiate-call")
async def initiate_call_endpoint(
    phone: str,
    contact_id: str = None,
    topic: str = None,
    context: str = None
):
    """Initiate an outbound voice call"""
    try:
        result = initiate_voice_call(
            phone=phone,
            contact_id=contact_id,
            topic=topic,
            context=context
        )
        
        if result['success']:
            return {
                "status": "success",
                "message": "Call initiated successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to initiate call'))
            
    except Exception as e:
        logger.error(f"Error initiating call: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/voice/call-status/{call_sid}")
async def get_call_status_endpoint(call_sid: str):
    """Get the status of a voice call"""
    try:
        result = get_call_status(call_sid)
        
        if result['success']:
            return {
                "status": "success",
                "data": result
            }
        else:
            raise HTTPException(status_code=404, detail=result.get('error', 'Call status not found'))
            
    except Exception as e:
        logger.error(f"Error getting call status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/voice/dashboard-data")
async def get_voice_dashboard_data_endpoint():
    """Get aggregated data for the voice operations dashboard"""
    try:
        result = get_voice_dashboard_data()
        
        if result['success']:
            return {
                "status": "success",
                "data": result['dashboard_data']
            }
        else:
            return {
                "status": "success",
                "data": {
                    "total_calls": 0,
                    "active_calls": 0,
                    "recent_calls": [],
                    "active_call_details": [],
                    "analytics": {
                        "success_rate": 0,
                        "average_duration": 0,
                        "total_duration": 0
                    }
                },
                "message": "No CRM connection - showing mock data"
            }
            
    except Exception as e:
        logger.error(f"Error getting voice dashboard data: {e}")
        return {
            "status": "success",
            "data": {
                "total_calls": 0,
                "active_calls": 0,
                "recent_calls": [],
                "active_call_details": [],
                "analytics": {
                    "success_rate": 0,
                    "average_duration": 0,
                    "total_duration": 0
                }
            },
            "message": f"Error getting data: {e}"
        }

@app.post("/voice/call-with-context")
async def call_with_context_endpoint(
    phone: str,
    company: str,
    contact_name: str = None,
    contact_id: str = None,
    include_intel: bool = True
):
    """Initiate call with pre-call intelligence context"""
    try:
        result = call_with_context(
            phone=phone,
            company=company,
            contact_name=contact_name,
            contact_id=contact_id,
            include_intel=include_intel
        )
        
        if result['success']:
            return {
                "status": "success",
                "message": "Contextual call initiated successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to initiate contextual call'))
            
    except Exception as e:
        logger.error(f"Error initiating contextual call: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Voice MVP Server...")
    print("📊 Dashboard: http://localhost:8000/voice/dashboard-data")
    print("📖 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)



