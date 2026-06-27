// ========== CONFIG ==========
const BACKEND_URL = 'https://YOUR_VERCEL_APP.vercel.app';

// ========== GLOBAL STATE ==========
let currentVideoId = null;
let currentVideoTitle = '';
let currentAudioUrl = null;
let activeTab = 'youtube';

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', async () => {
  await checkYouTubeVideo();
});

// ========== TAB SWITCHING ==========
function switchTab(tab) {
  activeTab = tab;
  
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  
  document.getElementById('youtubeSection').classList.toggle('hidden', tab !== 'youtube');
  document.getElementById('localSection').classList.toggle('hidden', tab !== 'local');
}

// ========== CHECK YOUTUBE VIDEO ==========
async function checkYouTubeVideo() {
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    
    if (tab.url && tab.url.includes('youtube.com/watch')) {
      const url = new URL(tab.url);
      currentVideoId = url.searchParams.get('v');
      currentVideoTitle = tab.title.replace(' - YouTube', '');
      
      document.getElementById('videoInfo').innerHTML = `
        <strong>🎬 ${currentVideoTitle.substring(0, 60)}...</strong><br>
        <span style="color:#667eea">Video ID: ${currentVideoId}</span>
      `;
    } else {
      document.getElementById('videoInfo').innerHTML = `
        <span style="color:#ff4757">⚠️ Open a YouTube video first!</span>
      `;
      document.getElementById('translateBtn').disabled = true;
    }
  } catch (e) {
    console.error('Error:', e);
  }
}

// ========== FILE SELECTION ==========
document.getElementById('videoFile')?.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) {
    document.getElementById('fileName').textContent = `📄 ${file.name}`;
  }
});

// ========== START TRANSLATION ==========
async function startTranslation() {
  const btn = document.getElementById('translateBtn');
  const status = document.getElementById('status');
  const lang = document.getElementById('targetLang').value;
  const voice = document.getElementById('voiceStyle').value;
  
  btn.disabled = true;
  
  try {
    if (activeTab === 'youtube') {
      await translateYouTube(lang, voice);
    } else {
      await translateLocal(lang, voice);
    }
  } catch (error) {
    status.innerHTML = `<span class="error">❌ Error: ${error.message}</span>`;
    btn.disabled = false;
  }
}

// ========== TRANSLATE YOUTUBE ==========
async function translateYouTube(lang, voice) {
  const status = document.getElementById('status');
  
  status.innerHTML = `<span class="loading">⏳ Step 1/4: Getting video info...</span>`;
  
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  
  status.innerHTML = `<span class="loading">⏳ Step 2/4: Extracting audio (this may take 1-2 min)...</span>`;
  
  const response = await fetch(`${BACKEND_URL}/translate/youtube`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_id: currentVideoId,
      target_language: lang,
      voice_style: voice
    })
  });
  
  if (!response.ok) throw new Error('Backend error');
  
  status.innerHTML = `<span class="loading">⏳ Step 3/4: Translating with AI...</span>`;
  
  const data = await response.json();
  
  status.innerHTML = `<span class="loading">⏳ Step 4/4: Generating voice...</span>`;
  
  await pollForResult(data.job_id);
}

// ========== TRANSLATE LOCAL VIDEO ==========
async function translateLocal(lang, voice) {
  const fileInput = document.getElementById('videoFile');
  const file = fileInput.files[0];
  
  if (!file) {
    throw new Error('Please select a video file first!');
  }
  
  const status = document.getElementById('status');
  status.innerHTML = `<span class="loading">⏳ Uploading video...</span>`;
  
  const formData = new FormData();
  formData.append('video', file);
  formData.append('target_language', lang);
  formData.append('voice_style', voice);
  
  const response = await fetch(`${BACKEND_URL}/translate/local`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) throw new Error('Upload failed');
  
  const data = await response.json();
  await pollForResult(data.job_id);
}

// ========== POLL FOR RESULT ==========
async function pollForResult(jobId) {
  const status = document.getElementById('status');
  const btn = document.getElementById('translateBtn');
  
  const checkStatus = async () => {
    const response = await fetch(`${BACKEND_URL}/status/${jobId}`);
    const data = await response.json();
    
    if (data.status === 'completed') {
      currentAudioUrl = data.audio_url;
      
      status.innerHTML = `<span class="success">✅ Translation Complete!</span>`;
      
      const player = document.getElementById('audioPlayer');
      player.src = data.audio_url;
      player.style.display = 'block';
      player.play();
      
      document.getElementById('downloadBtn').classList.remove('hidden');
      
      btn.disabled = false;
      btn.textContent = '🔄 Translate Another';
      
    } else if (data.status === 'failed') {
      throw new Error(data.error || 'Translation failed');
    } else {
      status.innerHTML = `<span class="loading">⏳ ${data.message || 'Processing...'} (${data.progress || 0}%)</span>`;
      setTimeout(checkStatus, 3000);
    }
  };
  
  await checkStatus();
}

// ========== DOWNLOAD AUDIO ==========
function downloadAudio() {
  if (!currentAudioUrl) return;
  
  chrome.downloads.download({
    url: currentAudioUrl,
    filename: `voiceswap-translated-${Date.now()}.mp3`
  });
}