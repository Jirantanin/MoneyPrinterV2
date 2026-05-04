// -------------------------------------------------------------------------
// State
// -------------------------------------------------------------------------
let episodeId = null;
let pollInterval = null;
let podcastEventSource = null;
let isGenerating = false;
let selectedLanguage = 'English';
let selectedTtsSource = 'edge';
let currentEpisodeStatus = 'idle';
let isCurrentEpisodeUploaded = false;
let hasAutoLoadedEpisode = false;
let shouldLoadVideoPreview = false;
let podcastLogs = [];
let currentSceneCount = 0;
let currentAssetStatuses = [];
let regeneratingSceneIndices = new Set();
let currentMetadata = {};
let currentCreativeDirection = '';
let podcastSystemSettings = null;
let podcastSettingsLoadPromise = null;
let activeDialogResolver = null;
let activeDialogType = null;
const STEP_NAMES = [
  "Generate Script",
  "Generate Assets",
  "Generate Metadata",
  "Generate Thumbnail",
  "Render Video",
];

// step_states[i] = { status: 'pending'|'running'|'done'|'error', message: '' }
let stepStates = STEP_NAMES.map(name => ({ name, status: 'pending', message: '' }));

// -------------------------------------------------------------------------
// Mode toggle
// -------------------------------------------------------------------------
function onModeChange() {
  const isStep = document.getElementById('modeToggle').checked;
  const track = document.getElementById('modeTrack');
  const thumb = document.getElementById('modeThumb');
  const badge = document.getElementById('modeBadge');
  const autoLabel = document.getElementById('modeAutoLabel');
  const stepLabel = document.getElementById('modeStepLabel');

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

function onInputModeChange() {
  const isScript = document.getElementById('inputModeToggle').checked;
  const thumb = document.getElementById('inputModeThumb');

  // Move toggle thumb
  thumb.style.left = isScript ? '1.75rem' : '0.25rem';

  // Show/hide field sections
  document.getElementById('topicModeFields').classList.toggle('hidden', isScript);
  document.getElementById('scriptModeFields').classList.toggle('hidden', !isScript);
  if (!isScript) {
    document.getElementById('scriptModeFields').style.display = '';
  } else {
    document.getElementById('scriptModeFields').style.display = 'flex';
  }

  // Update label styles
  document.getElementById('inputModeTopicLabel').className =
    `text-sm font-medium ${isScript ? 'text-subtext' : 'text-accent'}`;
  document.getElementById('inputModeScriptLabel').className =
    `text-sm font-medium ${isScript ? 'text-accent' : 'text-subtext'}`;
}

function lockModeToggle(lock) {
  const toggle = document.getElementById('modeToggle');
  const label = document.getElementById('modeToggleLabel');
  toggle.disabled = lock;
  label.style.opacity = lock ? '0.5' : '1';
  label.style.cursor = lock ? 'not-allowed' : 'pointer';
  label.style.pointerEvents = lock ? 'none' : '';
}

function closePodcastStream() {
  if (podcastEventSource) {
    podcastEventSource.close();
    podcastEventSource = null;
  }
}

function canResumeEpisode(data) {
  if (!data || !data.episode_id || isGenerating) return false;
  if (data.status === 'done' || data.status === 'uploaded') return false;
  if (typeof data.can_resume === 'boolean') return data.can_resume;
  return Array.isArray(data.step_states) && data.step_states.some(step => step.status !== 'done');
}

function updateResumeButton(data) {
  const btn = document.getElementById('resumeBtn');
  if (!btn) return;
  if (canResumeEpisode(data)) {
    btn.classList.remove('hidden');
  } else {
    btn.classList.add('hidden');
  }
}

function setModeValue(mode) {
  const toggle = document.getElementById('modeToggle');
  toggle.checked = mode === 'step';
  onModeChange();
}

function newEpisode() {
  episodeId = null;
  document.getElementById('topicInput').value = '';
  document.getElementById('creativeDirectionInput').value = '';
  document.getElementById('scriptTitleInput').value = '';
  document.getElementById('scriptInput').value = '';
  resetUI();
  setLanguage('English');
  setTtsSource('edge');
  setModeValue('auto');
  const isScript = document.getElementById('inputModeToggle').checked;
  document.getElementById(isScript ? 'scriptTitleInput' : 'topicInput').focus();
}

function resetUI() {
  closePodcastStream();
  stopPolling();
  stepStates = STEP_NAMES.map(name => ({ name, status: 'pending', message: '' }));
  currentEpisodeStatus = 'idle';
  isCurrentEpisodeUploaded = false;
  hasAutoLoadedEpisode = false;
  shouldLoadVideoPreview = false;
  currentSceneCount = 0;
  currentAssetStatuses = [];
  regeneratingSceneIndices = new Set();
  currentCreativeDirection = '';
  renderStepsPanel();

  // Hide approve banner
  document.getElementById('approveBanner').classList.add('hidden');
  document.getElementById('resumeBtn').classList.add('hidden');
  document.getElementById('creativeDirectionInput').disabled = false;

  // Clear image gallery
  renderImageGallery();

  // Clear script panel
  document.getElementById('scriptPanel').innerHTML =
    '<p id="noScriptMsg" class="text-subtext text-sm">Script will appear after generation begins.</p>';

  // Hide metadata panel
  clearMetadataView();
  clearThumbnailStudio();
  document.getElementById('videoPreviewPlayer').pause();
  document.getElementById('videoPreviewPlayer').removeAttribute('src');
  document.getElementById('videoPreviewPlayer').load();
  document.getElementById('videoPreviewPlayer').classList.add('hidden');
  document.getElementById('videoPreviewSkeleton').classList.remove('hidden');
  document.getElementById('videoPreviewStatus').textContent = 'Waiting for render';

  // Reset manual upload row
  hideManualUploadRow();
  const markBtn = document.getElementById('markUploadedBtn');
  if (markBtn) {
    markBtn.disabled = false;
    markBtn.textContent = 'Mark as Uploaded โ“';
    markBtn.classList.remove('bg-gray-600');
    markBtn.classList.add('bg-emerald-600');
  }
  const markStatusEl = document.getElementById('markUploadedStatus');
  if (markStatusEl) markStatusEl.textContent = '';

  // Hide episode dir
  document.getElementById('episodeDirInfo').classList.add('hidden');
  clearPodcastLogs();
}

function applyEpisodeState(data) {
  currentEpisodeStatus = data.status || 'idle';
  isCurrentEpisodeUploaded = !!data.is_uploaded;
  episodeId = data.episode_id || episodeId;
  setLanguage(data.language || data.metadata?.language || 'English');
  setTtsSource(data.tts_source || data.metadata?.tts_source || 'edge');
  setModeValue(data.mode || 'auto');
  currentSceneCount = data.scene_count || (Array.isArray(data.scenes) ? data.scenes.length : 0);
  currentAssetStatuses = Array.isArray(data.asset_statuses) ? data.asset_statuses : [];
  stepStates = (data.step_states || STEP_NAMES.map(name => ({ name, status: 'pending', message: '' })))
    .map((step, index) => ({
      name: step.name || STEP_NAMES[index],
      status: step.status || 'pending',
      message: step.message || '',
    }));
  renderStepsPanel();
  renderImageGallery();

  document.getElementById('topicInput').value = data.topic || '';
  currentCreativeDirection = data.creative_direction || '';
  document.getElementById('creativeDirectionInput').value = currentCreativeDirection;
  if (data.visual_style !== undefined) {
    document.getElementById('visualStyleSelect').value = data.visual_style;
  }
  if (data.scenes && data.scenes.length > 0) renderScript(data.scenes);
  else document.getElementById('scriptPanel').innerHTML =
    '<p id="noScriptMsg" class="text-subtext text-sm">Script will appear after generation begins.</p>';
  if (data.metadata && Object.keys(data.metadata).length > 0) renderMetadata(data.metadata);
  else clearMetadataView();
  if (data.thumbnail_url || (data.status === 'done' || data.status === 'uploaded')) {
    renderThumbnailStudio(data.thumbnail_prompt_pack, data.thumbnail_url);
  } else {
    clearThumbnailStudio();
  }
  renderVideoPreview(shouldLoadVideoPreview ? data.final_video_url : null);
  if (data.episode_dir) showEpisodeDir(data.episode_dir);
  if (data.status === 'done' || data.status === 'partial' || data.status === 'uploaded') {
    showManualUploadRow(data.episode_dir);
  } else {
    hideManualUploadRow();
  }
  if (isCurrentEpisodeUploaded || data.status === 'uploaded') {
    const btn = document.getElementById('markUploadedBtn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Uploaded โ“';
      btn.classList.remove('bg-emerald-600');
      btn.classList.add('bg-gray-600');
      const uploadedAt = data.uploaded_at
        ? new Date(data.uploaded_at).toLocaleString()
        : 'previously';
      document.getElementById('markUploadedStatus').textContent = `Uploaded ${uploadedAt}`;
    }
  }
  setPodcastLogs(data.logs || []);
  updateResumeButton(data);
  fetchEpisodeImages();
}

function setLanguage(lang) {
  selectedLanguage = lang;
  const enBtn = document.getElementById('langBtnEn');
  const thBtn = document.getElementById('langBtnTh');
  if (lang === 'Thai') {
    enBtn.classList.remove('bg-overlay', 'text-highlight');
    enBtn.classList.add('bg-charcoal', 'text-subtext');
    thBtn.classList.remove('bg-charcoal', 'text-subtext');
    thBtn.classList.add('bg-overlay', 'text-highlight');
  } else {
    thBtn.classList.remove('bg-overlay', 'text-highlight');
    thBtn.classList.add('bg-charcoal', 'text-subtext');
    enBtn.classList.remove('bg-charcoal', 'text-subtext');
    enBtn.classList.add('bg-overlay', 'text-highlight');
  }
  syncTtsSourceUI();
}

function setTtsSource(source) {
  if (selectedLanguage !== 'Thai' && (source === 'elevenlabs' || source === 'gemini')) {
    selectedTtsSource = 'edge';
  } else {
    selectedTtsSource = source;
  }
  syncTtsSourceUI();
}

function syncTtsSourceUI() {
  const edgeBtn = document.getElementById('ttsBtnEdge');
  const elevenBtn = document.getElementById('ttsBtnElevenLabs');
  const geminiBtn = document.getElementById('ttsBtnGemini');
  const hint = document.getElementById('ttsSourceHint');
  if (!edgeBtn || !elevenBtn || !hint) return;

  const thaiEnabled = selectedLanguage === 'Thai';
  if (!thaiEnabled) {
    selectedTtsSource = 'edge';
  }

  edgeBtn.disabled = false;
  edgeBtn.classList.toggle('bg-overlay', selectedTtsSource === 'edge');
  edgeBtn.classList.toggle('text-highlight', selectedTtsSource === 'edge');
  edgeBtn.classList.toggle('bg-charcoal', selectedTtsSource !== 'edge');
  edgeBtn.classList.toggle('text-subtext', selectedTtsSource !== 'edge');

  elevenBtn.disabled = !thaiEnabled;
  elevenBtn.classList.toggle('opacity-50', !thaiEnabled);
  elevenBtn.classList.toggle('cursor-not-allowed', !thaiEnabled);
  elevenBtn.classList.toggle('bg-overlay', thaiEnabled && selectedTtsSource === 'elevenlabs');
  elevenBtn.classList.toggle('text-highlight', thaiEnabled && selectedTtsSource === 'elevenlabs');
  elevenBtn.classList.toggle('bg-charcoal', !thaiEnabled || selectedTtsSource !== 'elevenlabs');
  elevenBtn.classList.toggle('text-subtext', !thaiEnabled || selectedTtsSource !== 'elevenlabs');

  if (geminiBtn) {
    geminiBtn.disabled = !thaiEnabled;
    geminiBtn.classList.toggle('opacity-50', !thaiEnabled);
    geminiBtn.classList.toggle('cursor-not-allowed', !thaiEnabled);
    geminiBtn.classList.toggle('bg-overlay', thaiEnabled && selectedTtsSource === 'gemini');
    geminiBtn.classList.toggle('text-highlight', thaiEnabled && selectedTtsSource === 'gemini');
    geminiBtn.classList.toggle('bg-charcoal', !thaiEnabled || selectedTtsSource !== 'gemini');
    geminiBtn.classList.toggle('text-subtext', !thaiEnabled || selectedTtsSource !== 'gemini');
  }

  if (!thaiEnabled) {
    hint.textContent = 'English currently uses Edge only.';
  } else if (selectedTtsSource === 'elevenlabs') {
    hint.textContent = 'Thai will use ElevenLabs first.';
  } else if (selectedTtsSource === 'gemini') {
    hint.textContent = 'Thai will use Gemini 2.5 Flash TTS.';
  } else {
    hint.textContent = 'Thai will use Edge directly.';
  }
}

function onGenerationEnd() {
  isGenerating = false;
  document.getElementById('topicInput').disabled = false;
  document.getElementById('creativeDirectionInput').disabled = false;
  document.getElementById('generateBtn').disabled = false;
  document.getElementById('resumeBtn').disabled = false;
  document.getElementById('cancelBtn').classList.add('hidden');
  document.getElementById('scriptInput').disabled = false;
  document.getElementById('scriptTitleInput').disabled = false;
  document.getElementById('scriptGenerateBtn').disabled = false;
  document.getElementById('scriptCancelBtn').classList.add('hidden');
  lockModeToggle(false);
  document.getElementById('approveBanner').classList.add('hidden');
}

// -------------------------------------------------------------------------
// Generate
// -------------------------------------------------------------------------
function handleEvent(evt) {
  if (evt.type === 'step_start') {
    const i = evt.step;
    if (i >= 0 && i < stepStates.length) {
      stepStates[i].status = 'running';
      stepStates[i].message = '';
      updateStepUI(i);
    }
  } else if (evt.type === 'step_done') {
    const i = evt.step;
    if (i >= 0 && i < stepStates.length) {
      stepStates[i].status = 'done';
      updateStepUI(i);
      if (i === 0 || i === 3) fetchEpisodeData();
      if (i === 2) {
        shouldLoadVideoPreview = true;
        fetchEpisodeData();
      }
    }
  } else if (evt.type === 'step_error') {
    const i = evt.step;
    if (i >= 0 && i < stepStates.length) {
      stepStates[i].status = 'error';
      stepStates[i].message = evt.error || 'Error';
      updateStepUI(i);
    }
  } else if (evt.type === 'log') {
    const i = typeof evt.step === 'number' ? evt.step : -1;
    if (i >= 0 && i < stepStates.length && stepStates[i].status === 'running') {
      stepStates[i].message = evt.message || '';
      updateStepUI(i);
    }
    appendPodcastLog(evt.message || '');
  } else if (evt.type === 'waiting_approval') {
    const nextName = evt.next_name || STEP_NAMES[evt.next_step] || 'next step';
    document.getElementById('approveNextLabel').textContent = `Next: ${nextName}`;
    document.getElementById('approveBanner').classList.remove('hidden');
  } else if (evt.type === 'resume') {
    appendPodcastLog(evt.message || 'Resuming pipeline...');
  } else if (evt.type === 'thumbnail_updated') {
    fetchEpisodeData();
  }
}

// -------------------------------------------------------------------------
// Image polling
// -------------------------------------------------------------------------
let renderedImages = new Set();

function showError(msg) {
  const status = document.getElementById('uploadStatus');
  if (status) {
    status.className = 'text-sm text-rose';
    status.textContent = 'Error: ' + msg;
  } else {
    console.error('Error: ' + msg);
  }
}

// -------------------------------------------------------------------------
// Publish mode toggle
// -------------------------------------------------------------------------
function onPublishModeChange() {
  const mode = document.querySelector('input[name="publishMode"]:checked').value;
  const picker = document.getElementById('schedulePicker');
  if (mode === 'schedule') {
    picker.classList.remove('hidden');
    // Pre-fill with tomorrow same time as a sensible default
    if (!document.getElementById('scheduleDateTime').value) {
      const tomorrow = new Date(Date.now() + 86400000);
      tomorrow.setSeconds(0, 0);
      // datetime-local format: YYYY-MM-DDTHH:MM
      document.getElementById('scheduleDateTime').value =
        tomorrow.toISOString().slice(0, 16);
    }
  } else {
    picker.classList.add('hidden');
  }
}

// -------------------------------------------------------------------------
// Upload
// -------------------------------------------------------------------------
window.addEventListener('load', () => {
  renderStepsPanel();
  syncTtsSourceUI();
  initPodcastSettingsTooltips();
  loadPodcastSettings();
  fetchEpisodeLibrary();

  const overlay = document.getElementById('podcastDialogOverlay');
  const card = document.getElementById('podcastDialogCard');
  const confirmBtn = document.getElementById('podcastDialogConfirm');
  const cancelBtn = document.getElementById('podcastDialogCancel');
  const closeBtn = document.getElementById('podcastDialogClose');
  const settingsOverlay = document.getElementById('podcastSettingsOverlay');
  const settingsCard = document.getElementById('podcastSettingsCard');
  const settingsCloseBtn = document.getElementById('podcastSettingsClose');
  const settingsCancelBtn = document.getElementById('podcastSettingsCancel');
  const settingsSaveBtn = document.getElementById('podcastSettingsSave');
  const settingsResetBtn = document.getElementById('podcastSettingsReset');

  if (overlay && card && confirmBtn && cancelBtn && closeBtn) {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) closeDialog(false);
    });
    card.addEventListener('click', (event) => event.stopPropagation());
    confirmBtn.addEventListener('click', () => closeDialog(true));
    cancelBtn.addEventListener('click', () => closeDialog(false));
    closeBtn.addEventListener('click', () => closeDialog(false));
  }

  if (settingsOverlay && settingsCard && settingsCloseBtn && settingsCancelBtn && settingsSaveBtn && settingsResetBtn) {
    settingsOverlay.addEventListener('click', (event) => {
      if (event.target === settingsOverlay) closePodcastSettings();
    });
    settingsCard.addEventListener('click', (event) => event.stopPropagation());
    settingsCloseBtn.addEventListener('click', closePodcastSettings);
    settingsCancelBtn.addEventListener('click', closePodcastSettings);
    settingsSaveBtn.addEventListener('click', async () => {
      settingsSaveBtn.disabled = true;
      showPodcastSettingsStatus('Saving system settings...', 'muted');
      try {
        await savePodcastSettings();
      } finally {
        settingsSaveBtn.disabled = false;
      }
    });
    settingsResetBtn.addEventListener('click', () => {
      resetPodcastSettingsToDefaults();
    });
  }

  document.addEventListener('keydown', (event) => {
    const settingsOpen = !document.getElementById('podcastSettingsOverlay')?.classList.contains('hidden');
    const dialogOpen = !document.getElementById('podcastDialogOverlay')?.classList.contains('hidden');
    if (!settingsOpen && !dialogOpen) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      if (settingsOpen) closePodcastSettings();
      else closeDialog(false);
    }
  });

  // Allow Enter key to trigger generate
  document.getElementById('topicInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startGeneration();
  });
});
