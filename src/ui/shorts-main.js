// =========================================================================
// YouTube Shorts Tab โ€” namespaced JS
// =========================================================================
var shorts_currentShortId = null;
var shorts_isGenerating = false;
var shorts_currentStatus = 'idle';
var shorts_eventSource = null;
var shorts_imagePollInterval = null;
var shorts_renderedImages = new Set();
var shorts_hasAutoLoaded = false;
var shorts_currentEpisodeData = {};
var shorts_youtubeAuth = { authenticated: false, message: '' };

var SHORTS_STEP_NAMES = [
  "Generate Topic",
  "Generate Script",
  "Generate Hook",
  "Generate Metadata",
  "Generate Image Prompts",
  "Generate Images",
  "Text-to-Speech",
  "Generate Subtitles",
  "Render Video",
];

var shorts_stepStates = SHORTS_STEP_NAMES.map(function(name) { return { name: name, status: 'pending', message: '' }; });

function shorts_onModeChange() {
  var isStep = document.getElementById('shorts-modeToggle').checked;
  var track = document.getElementById('shorts-modeTrack');
  var thumb = document.getElementById('shorts-modeThumb');
  var badge = document.getElementById('shorts-modeBadge');
  var autoLabel = document.getElementById('shorts-modeAutoLabel');
  var stepLabel = document.getElementById('shorts-modeStepLabel');

  if (isStep) {
    track.style.backgroundColor = 'rgba(255, 211, 107, 0.34)';
    thumb.style.left = '1.75rem';
    thumb.style.backgroundColor = '#161004';
    badge.textContent = 'Pauses after each step for your approval';
    badge.className = 'state-pill is-step ml-auto text-xs';
    autoLabel.className = 'text-sm font-medium text-subtext';
    stepLabel.className = 'text-sm font-semibold text-[color:var(--ui-warn)]';
  } else {
    track.style.backgroundColor = '';
    thumb.style.left = '0.25rem';
    thumb.style.backgroundColor = '';
    badge.textContent = 'Runs all steps automatically';
    badge.className = 'state-pill is-auto ml-auto text-xs';
    autoLabel.className = 'text-sm font-semibold text-accent';
    stepLabel.className = 'text-sm font-medium text-subtext';
  }
}

function shorts_lockModeToggle(lock) {
  var toggle = document.getElementById('shorts-modeToggle');
  var label = document.getElementById('shorts-modeToggleLabel');
  toggle.disabled = lock;
  label.style.opacity = lock ? '0.5' : '1';
  label.style.cursor = lock ? 'not-allowed' : 'pointer';
  label.style.pointerEvents = lock ? 'none' : '';
}

// Account loading
function shorts_onAccountChange() {
  var select = document.getElementById('shorts-accountSelect');
  var opt = select.options[select.selectedIndex];
  if (!opt || !opt.value) return;
  document.getElementById('shorts-nicheInput').value = opt.dataset.niche || '';
  document.getElementById('shorts-languageInput').value = opt.dataset.language || 'English';
}

// Steps UI
function shorts_newShort() {
  shorts_currentShortId = null;
  document.getElementById('shorts-topicInput').value = '';
  document.getElementById('shorts-topicInput').focus();
  shorts_resetUI();
}

function shorts_resetUI() {
  shorts_stepStates = SHORTS_STEP_NAMES.map(function(name) { return { name: name, status: 'pending', message: '' }; });
  shorts_currentStatus = 'idle';
  shorts_renderedImages = new Set();
  shorts_currentEpisodeData = {};
  shorts_renderStepsPanel();

  document.getElementById('shorts-approveBanner').classList.add('hidden');

  var gallery = document.getElementById('shorts-imageGallery');
  gallery.innerHTML = '<div id="shorts-noImagesMsg" class="col-span-6 flex items-center justify-center text-subtext text-sm h-24">No images yet</div>';

  var player = document.getElementById('shorts-videoPreviewPlayer');
  player.pause();
  player.removeAttribute('src');
  player.load();
  player.classList.add('hidden');
  document.getElementById('shorts-videoPreviewSkeleton').classList.remove('hidden');
  document.getElementById('shorts-videoPreviewStatus').textContent = 'Waiting for render';

  document.getElementById('shorts-metadataPanel').classList.add('hidden');
  document.getElementById('shorts-metadataContent').innerHTML = '';
  document.getElementById('shorts-reviewPanel').classList.add('hidden');
  document.getElementById('shorts-reviewContent').innerHTML = '';

  document.getElementById('shorts-uploadBtn').disabled = true;
  document.getElementById('shorts-uploadStatus').textContent = '';
  document.getElementById('shorts-runDirInfo').classList.add('hidden');

  document.getElementById('shorts-logOutput').innerHTML = '<p class="text-overlay">Pipeline log will appear here.</p>';
  shorts_applyYoutubeAuthStatus();
}

function shorts_onGenerationEnd() {
  shorts_isGenerating = false;
  document.getElementById('shorts-generateBtn').disabled = false;
  document.getElementById('shorts-cancelBtn').classList.add('hidden');
  shorts_lockModeToggle(false);
  document.getElementById('shorts-approveBanner').classList.add('hidden');
}

// Cancel
function shorts_startImagePolling() {
  shorts_renderedImages = new Set();
  shorts_imagePollInterval = setInterval(async function() {
    if (!shorts_currentShortId) return;
    await shorts_fetchImages();
  }, 2000);
}

function shorts_stopImagePolling() {
  if (shorts_imagePollInterval) { clearInterval(shorts_imagePollInterval); shorts_imagePollInterval = null; }
  if (shorts_currentShortId) {
    setTimeout(shorts_fetchImages, 1000);
  }
}

function shorts_showError(msg) {
  var status = document.getElementById('shorts-uploadStatus');
  status.className = 'text-sm text-rose';
  status.textContent = 'Error: ' + msg;
  shorts_appendLog('Error: ' + msg, true);
}

// Init Shorts on load
window.addEventListener('load', function() {
  shorts_renderStepsPanel();
  document.getElementById('shorts-topicInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') shorts_startGenerate();
  });
});
