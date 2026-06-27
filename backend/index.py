from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid

app = FastAPI(title="VoiceSwap AI - Free Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hugging Face Token (Vercel Environment Variable se)
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Jobs storage
jobs = {}

@app.post("/translate/youtube")
async def translate_youtube(
    background_tasks: BackgroundTasks,
    video_id: str = Form(...),
    target_language: str = Form("hi"),
    voice_style: str = Form("natural")
):
    """YouTube video translate karo"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "processing",
        "progress": 50,
        "message": "Processing...",
        "audio_url": None,
        "error": None
    }
    
    background_tasks.add_task(
        simulate_processing,
        job_id, video_id, target_language
    )
    
    return {"job_id": job_id, "status": "started"}

@app.post("/translate/local")
async def translate_local(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    target_language: str = Form("hi"),
    voice_style: str = Form("natural")
):
    """Local video translate karo"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "processing",
        "progress": 50,
        "message": "Processing uploaded video...",
        "audio_url": None,
        "error": None
    }
    
    background_tasks.add_task(
        simulate_processing,
        job_id, "local", target_language
    )
    
    return {"job_id": job_id, "status": "started"}

def simulate_processing(job_id, video_id, target_language):
    """Demo processing"""
    import time
    time.sleep(3)
    
    jobs[job_id] = {
        "status": "completed",
        "progress": 100,
        "message": "Translation complete! (Demo mode)",
        "audio_url": f"/download/{job_id}",
        "error": None
    }

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Job status check karo"""
    job = jobs.get(job_id, {
        "status": "not_found",
        "progress": 0,
        "message": "Job not found",
        "audio_url": None,
        "error": None
    })
    return job

@app.get("/download/{job_id}")
async def download_audio(job_id: str):
    """Demo audio download"""
    return JSONResponse({
        "message": "Demo mode - Real audio will be available in production",
        "job_id": job_id
    })

@app.get("/")
async def root():
    return {
        "message": "VoiceSwap AI Backend",
        "version": "1.0",
        "status": "running",
        "mode": "demo"
    }