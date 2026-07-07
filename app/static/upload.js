const voiceSelect = document.getElementById("voice-select");
const demoButton = document.getElementById("voice-demo-button");
const player = document.getElementById("voice-demo-player");
const statusText = document.getElementById("voice-demo-status");
const voices = Array.isArray(window.bookforgeVoices) ? window.bookforgeVoices : [];

function selectedVoice() {
  return voices.find((voice) => voice.id === voiceSelect?.value);
}

function updateDemoState() {
  const voice = selectedVoice();
  const previewUrl = voice?.preview_url;
  if (!demoButton || !player || !statusText) return;
  if (previewUrl) {
    demoButton.disabled = false;
    statusText.textContent = "";
  } else {
    demoButton.disabled = true;
    player.removeAttribute("src");
    statusText.textContent = "No demo audio URL was provided by MimikaStudio for this voice.";
  }
}

voiceSelect?.addEventListener("change", updateDemoState);
demoButton?.addEventListener("click", async () => {
  const voice = selectedVoice();
  if (!voice?.preview_url || !player) return;
  player.src = voice.preview_url;
  player.classList.add("visible");
  await player.play();
});
updateDemoState();
