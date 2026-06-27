console.log('VoiceSwap AI: Content script loaded');

function detectVideo() {
  const video = document.querySelector('video');
  if (video) {
    console.log('Video found:', video.src);
  }
}

detectVideo();

let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    setTimeout(detectVideo, 1000);
  }
}).observe(document, { subtree: true, childList: true });