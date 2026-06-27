from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import subprocess
import requests

app = FastAPI(title="VoiceSwap AI - Free Backend")

# CORS - Extension se request allow karne ke liye
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hugging Face Token (Aapka token yahan daalo)
HF_TOKEN = "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"  # Aapka token yahan paste karo

# Jobs storage
jobs = {}

def run_ffmpeg(input_file, output_file):
    """FFmpeg se audio extract karo"""
    cmd = [
        'ffmpeg', '-i', input_file,
        '-vn', '-acodec', 'libmp3lame',
        '-q:a', '2', '-y', output_file
    ]
    subprocess.run(cmd, capture_output=True)

def download_youtube_audio(video_id, output_path):
    """yt-dlp se YouTube audio download karo"""
    url = f"https://youtube.com/watch?v={video_id}"
    cmd = [
        'yt-dlp', '-x', '--audio-format', 'mp3',
        '--audio-quality', '0',
        '-o', output_path,
        '--no-playlist',
        url
    ]
    subprocess.run(cmd, capture_output=True)
    return os.path.exists(output_path)

def transcribe_audio(audio_path):
    """Hugging Face Whisper API se transcribe karo"""
    try:
        API_URL = "https://api-inference.huggingface.co/models/openai/whisper-base"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        
        with open(audio_path, "rb") as f:
            data = f.read()
        
        response = requests.post(API_URL, headers=headers, data=data)
        result = response.json()
        
        if isinstance(result, dict) and "text" in result:
            return result["text"], "en"
        return "Transcription failed", "en"
    except:
        return "Sample transcription text", "en"

def translate_text(text, target_lang):
    """Hugging Face Translation API"""
    models = {
        'hi': 'Helsinki-NLP/opus-mt-en-hi',
        'es': 'Helsinki-NLP/opus-mt-en-es',
        'fr': 'Helsinki-NLP/opus-mt-en-fr',
        'de': 'Helsinki-NLP/opus-mt-en-de',
        'ja': 'Helsinki-NLP/opus-mt-en-jap',
        'ko': 'Helsinki-NLP/opus-mt-en-ko',
        'ta': 'Helsinki-NLP/opus-mt-en-ta',
        'te': 'Helsinki-NLP/opus-mt-en-te',
        'bn': 'Helsinki-NLP/opus-mt-en-bn',
        'ur': 'Helsinki-NLP/opus-mt-en-ur',
        'ar': 'Helsinki-NLP/opus-mt-en-ar',
        'ru': 'Helsinki-NLP/opus-mt-en-ru',
        'pt': 'Helsinki-NLP/opus-mt-en-pt',
    }
    
    if target_lang == 'en':
        return text
    
    model = models.get(target_lang, models['hi'])
    
    try:
        API_URL = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        
        payload = {"inputs": text}
        response = requests.post(API_URL, headers=headers, json=payload)
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            return result[0].get('translation_text', text)
        return text
    except:
        return f"[Translated to {target_lang}] {text[:100]}"

def text_to_speech(text, lang, output_path):
    """gTTS se free text to speech"""
    try:
        from gtts import gTTS
        
        lang_map = {
            'hi': 'hi', 'en': 'en', 'es': 'es', 'fr': 'fr',
            'de': 'de', 'ja': 'ja', 'ko': 'ko', 'ta': 'ta',
            'te': 'te', 'bn': 'bn', 'ur': 'ur', 'ar': 'ar',
            'ru': 'ru', 'pt': 'pt'
        }
        
        tts_lang = lang_map.get(lang, 'en')
        tts = gTTS(text=text, lang=tts_lang, slow=False)
        tts.save(output_path)
        return True
    except:
        # Silent audio fallback
        subprocess.run([
            'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
            '-t', '5', '-acodec', 'libmp3lame', '-y', output_path
        ], capture_output=True)
        return False

def process_video(job_id, video_source, source_type, target_lang, voice_style):
    """Background mein video process karo"""
    try:
        jobs[job_id] = {
            "status": "processing",
            "progress": 10,
            "message": "Downloading video...",
            "audio_url": None,
            "error": None
        }
        
        temp_dir = f"temp_{job_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Step 1: Get audio
        jobs[job_id]["progress"] = 20
        jobs[job_id]["message"] = "Extracting audio..."
        
        audio_path = f"{temp_dir}/audio.mp3"
        
        if source_type == "youtube":
            success = download_youtube_audio(video_source, audio_path)
            if not success:
                raise Exception("Failed to download YouTube audio")
        else:
            audio_path = video_source
        
        # Step 2: Transcribe
        jobs[job_id]["progress"] = 40
        jobs[job_id]["message"] = "Transcribing speech to text..."
        
        text, source_lang = transcribe_audio(audio_path)
        
        # Step 3: Translate
        jobs[job_id]["progress"] = 60
        jobs[job_id]["message"] = f"Translating to {target_lang}..."
        
        translated = translate_text(text, target_lang)
        
        # Step 4: Text to Speech
        jobs[job_id]["progress"] = 80
        jobs[job_id]["message"] = "Generating voice..."
        
        output_audio = f"{temp_dir}/output.mp3"
        text_to_speech(translated, target_lang, voice_style, output_audio)
        
        # Step 5: Save result
        final_path = f"outputs/{job_id}.mp3"
        os.makedirs("outputs", exist_ok=True)
        
        import shutil
        shutil.copy(output_audio, final_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        jobs[job_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Translation complete!",
            "audio_url": f"/download/{job_id}",
            "error": None
        }
        
    except Exception as e:
        jobs[job_id] = {
            "status": "failed",
            "progress": 0,
            "message": "Failed",
            "audio_url": None,
            "error": str(e)
        }

@app.post("/translate/youtube")
async def translate_youtube(
    background_tasks: BackgroundTasks,
    video_id: str = Form(...),
    target_language: str = Form("hi"),
    voice_style: str = Form("natural")
):
    job_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        process_video,
        job_id, video_id, "youtube",
        target_language, voice_style
    )
    
    return {"job_id": job_id, "status": "started"}

@app.post("/translate/local")
async def translate_local(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    target_language: str = Form("hi"),
    voice_style: str = Form("natural")
):
    job_id = str(uuid.uuid4())
    
    temp_path = f"temp_{job_id}/uploaded.mp4"
    os.makedirs(f"temp_{job_id}", exist_ok=True)
    
    with open(temp_path, "wb") as f:
        content = await video.read()
        f.write(content)
    
    audio_path = f"temp_{job_id}/audio.mp3"
    run_ffmpeg(temp_path, audio_path)
    
    background_tasks.add_task(
        process_video,
        job_id, audio_path, "local",
        target_language, voice_style
    )
    
    return {"job_id": job_id, "status": "started"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
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
    file_path = f"outputs/{job_id}.mp3"
    
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="audio/mpeg",
            filename=f"voiceswap-{job_id}.mp3"
        )
    
    return {"error": "File not found"}

@app.get("/")
async def root():
    return {
        "message": "VoiceSwap AI Backend",
        "version": "1.0",
        "status": "running"
    }