// -------------------------------------------------------------------------
// State
// -------------------------------------------------------------------------
let episodeIdV2 = null;
let pollIntervalV2 = null;
let podcastEventSourceV2 = null;
let isGeneratingV2 = false;
let selectedLanguageV2 = 'English';
let selectedTtsSourceV2 = 'edge';
let currentEpisodeStatusV2 = 'idle';
let isCurrentEpisodeUploadedV2 = false;
let hasAutoLoadedEpisodeV2 = false;
let shouldLoadVideoPreviewV2 = false;
let podcastLogsV2 = [];
let currentSceneCountV2 = 0;
let currentAssetStatusesV2 = [];
let regeneratingSceneIndicesV2 = new Set();
let currentMetadataV2 = {};
let currentScriptQcV2 = {};
let currentCreativeDirectionV2 = '';
let podcastV2SystemSettings = null;
let podcastV2SettingsLoadPromise = null;
let activeDialogResolverV2 = null;
let activeDialogTypeV2 = null;
const STEP_NAMES_V2 = [
  "Generate Script",
  "Generate Assets",
  "Generate Metadata",
  "Generate Thumbnail",
  "Render Video",
];

let stepStatesV2 = STEP_NAMES_V2.map(name => ({ name, status: 'pending', message: '' }));

// -------------------------------------------------------------------------
// Mode toggle
// -------------------------------------------------------------------------
function onModeChangeV2() {
  const isStep = document.getElementById('modeToggleV2').checked;
  const track = document.getElementById('modeTrackV2');
  const thumb = document.getElementById('modeThumbV2');
  const badge = document.getElementById('modeBadgeV2');
  const autoLabel = document.getElementById('modeAutoLabelV2');
  const stepLabel = document.getElementById('modeStepLabelV2');

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

function onInputModeChangeV2() {
  const isScript = document.getElementById('inputModeToggleV2').checked;
  const thumb = document.getElementById('inputModeThumbV2');

  thumb.style.left = isScript ? '1.75rem' : '0.25rem';

  document.getElementById('topicModeFieldsV2').classList.toggle('hidden', isScript);
  document.getElementById('scriptModeFieldsV2').classList.toggle('hidden', !isScript);
  if (!isScript) {
    document.getElementById('scriptModeFieldsV2').style.display = '';
  } else {
    document.getElementById('scriptModeFieldsV2').style.display = 'flex';
  }

  document.getElementById('inputModeTopicLabelV2').className =
    `text-sm font-medium ${isScript ? 'text-subtext' : 'text-accent'}`;
  document.getElementById('inputModeScriptLabelV2').className =
    `text-sm font-medium ${isScript ? 'text-accent' : 'text-subtext'}`;
}

function lockModeToggleV2(lock) {
  const toggle = document.getElementById('modeToggleV2');
  const label = document.getElementById('modeToggleLabelV2');
  toggle.disabled = lock;
  label.style.opacity = lock ? '0.5' : '1';
  label.style.cursor = lock ? 'not-allowed' : 'pointer';
  label.style.pointerEvents = lock ? 'none' : '';
}

function closePodcastStreamV2() {
  if (podcastEventSourceV2) {
    podcastEventSourceV2.close();
    podcastEventSourceV2 = null;
  }
}

function canResumeEpisodeV2(data) {
  if (!data || !data.episode_id || isGeneratingV2) return false;
  if (data.status === 'done' || data.status === 'uploaded') return false;
  if (typeof data.can_resume === 'boolean') return data.can_resume;
  return Array.isArray(data.step_states) && data.step_states.some(step => step.status !== 'done');
}

function updateResumeButtonV2(data) {
  const btn = document.getElementById('resumeBtnV2');
  if (!btn) return;
  if (canResumeEpisodeV2(data)) {
    btn.classList.remove('hidden');
  } else {
    btn.classList.add('hidden');
  }
}

function setModeValueV2(mode) {
  const toggle = document.getElementById('modeToggleV2');
  toggle.checked = mode === 'step';
  onModeChangeV2();
}

function newEpisodeV2() {
  episodeIdV2 = null;
  document.getElementById('topicInputV2').value = '';
  document.getElementById('creativeDirectionInputV2').value = '';
  document.getElementById('scriptTitleInputV2').value = '';
  document.getElementById('scriptInputV2').value = '';
  resetUIV2();
  setLanguageV2('English');
  setTtsSourceV2('edge');
  setModeValueV2('auto');
  const isScript = document.getElementById('inputModeToggleV2').checked;
  document.getElementById(isScript ? 'scriptTitleInputV2' : 'topicInputV2').focus();
}

function resetUIV2() {
  closePodcastStreamV2();
  stopPollingV2();
  stepStatesV2 = STEP_NAMES_V2.map(name => ({ name, status: 'pending', message: '' }));
  currentEpisodeStatusV2 = 'idle';
  isCurrentEpisodeUploadedV2 = false;
  hasAutoLoadedEpisodeV2 = false;
  shouldLoadVideoPreviewV2 = false;
  currentSceneCountV2 = 0;
  currentAssetStatusesV2 = [];
  regeneratingSceneIndicesV2 = new Set();
  currentScriptQcV2 = {};
  currentCreativeDirectionV2 = '';
  renderStepsPanelV2();

  document.getElementById('approveBannerV2').classList.add('hidden');
  document.getElementById('resumeBtnV2').classList.add('hidden');
  document.getElementById('creativeDirectionInputV2').disabled = false;

  renderImageGalleryV2();

  document.getElementById('scriptPanelV2').innerHTML =
    '<p id="noScriptMsgV2" class="text-subtext text-sm">Script will appear after generation begins.</p>';
  renderScriptQcV2({});

  clearMetadataViewV2();
  clearThumbnailStudioV2();
  document.getElementById('videoPreviewPlayerV2').pause();
  document.getElementById('videoPreviewPlayerV2').removeAttribute('src');
  document.getElementById('videoPreviewPlayerV2').load();
  document.getElementById('videoPreviewPlayerV2').classList.add('hidden');
  document.getElementById('videoPreviewSkeletonV2').classList.remove('hidden');
  document.getElementById('videoPreviewStatusV2').textContent = 'Waiting for render';

  hideManualUploadRowV2();
  const markBtn = document.getElementById('markUploadedBtnV2');
  if (markBtn) {
    markBtn.disabled = false;
    markBtn.textContent = 'Mark as Uploaded ✓';
    markBtn.classList.remove('bg-gray-600');
    markBtn.classList.add('bg-emerald-600');
  }
  const markStatusEl = document.getElementById('markUploadedStatusV2');
  if (markStatusEl) markStatusEl.textContent = '';

  document.getElementById('episodeDirInfoV2').classList.add('hidden');
  clearPodcastLogsV2();
}

function applyEpisodeStateV2(data) {
  currentEpisodeStatusV2 = data.status || 'idle';
  isCurrentEpisodeUploadedV2 = !!data.is_uploaded;
  episodeIdV2 = data.episode_id || episodeIdV2;
  setLanguageV2(data.language || data.metadata?.language || 'English');
  setTtsSourceV2(data.tts_source || data.metadata?.tts_source || 'edge');
  setModeValueV2(data.mode || 'auto');
  currentSceneCountV2 = data.scene_count || (Array.isArray(data.scenes) ? data.scenes.length : 0);
  currentAssetStatusesV2 = Array.isArray(data.asset_statuses) ? data.asset_statuses : [];
  currentScriptQcV2 = data.script_qc || {};
  stepStatesV2 = (data.step_states || STEP_NAMES_V2.map(name => ({ name, status: 'pending', message: '' })))
    .map((step, index) => ({
      name: step.name || STEP_NAMES_V2[index],
      status: step.status || 'pending',
      message: step.message || '',
    }));
  renderStepsPanelV2();
  renderImageGalleryV2();

  document.getElementById('topicInputV2').value = data.topic || '';
  currentCreativeDirectionV2 = data.creative_direction || '';
  document.getElementById('creativeDirectionInputV2').value = currentCreativeDirectionV2;
  if (data.visual_style !== undefined) {
    document.getElementById('visualStyleSelectV2').value = data.visual_style;
  }
  if (data.scenes && data.scenes.length > 0) renderScriptV2(data.scenes);
  else document.getElementById('scriptPanelV2').innerHTML =
    '<p id="noScriptMsgV2" class="text-subtext text-sm">Script will appear after generation begins.</p>';
  renderScriptQcV2(currentScriptQcV2);
  if (data.metadata && Object.keys(data.metadata).length > 0) renderMetadataV2(data.metadata);
  else clearMetadataViewV2();
  if (data.thumbnail_url || (data.status === 'done' || data.status === 'uploaded')) {
    renderThumbnailStudioV2(data.thumbnail_prompt_pack, data.thumbnail_url);
  } else {
    clearThumbnailStudioV2();
  }
  renderVideoPreviewV2(shouldLoadVideoPreviewV2 ? data.final_video_url : null);
  if (data.episode_dir) showEpisodeDirV2(data.episode_dir);
  if (data.status === 'done' || data.status === 'partial' || data.status === 'uploaded') {
    showManualUploadRowV2(data.episode_dir);
  } else {
    hideManualUploadRowV2();
  }
  if (isCurrentEpisodeUploadedV2 || data.status === 'uploaded') {
    const btn = document.getElementById('markUploadedBtnV2');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Uploaded ✓';
      btn.classList.remove('bg-emerald-600');
      btn.classList.add('bg-gray-600');
      const uploadedAt = data.uploaded_at
        ? new Date(data.uploaded_at).toLocaleString()
        : 'previously';
      document.getElementById('markUploadedStatusV2').textContent = `Uploaded ${uploadedAt}`;
    }
  }
  setPodcastLogsV2(data.logs || []);
  updateResumeButtonV2(data);
  fetchEpisodeImagesV2();
}

function setLanguageV2(lang) {
  selectedLanguageV2 = lang;
  const enBtn = document.getElementById('langBtnEnV2');
  const thBtn = document.getElementById('langBtnThV2');
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
  syncTtsSourceUIV2();
}

function setTtsSourceV2(source) {
  if (selectedLanguageV2 !== 'Thai' && (source === 'elevenlabs' || source === 'gemini')) {
    selectedTtsSourceV2 = 'edge';
  } else {
    selectedTtsSourceV2 = source;
  }
  syncTtsSourceUIV2();
}

function syncTtsSourceUIV2() {
  const edgeBtn = document.getElementById('ttsBtnEdgeV2');
  const elevenBtn = document.getElementById('ttsBtnElevenLabsV2');
  const geminiBtn = document.getElementById('ttsBtnGeminiV2');
  const hint = document.getElementById('ttsSourceHintV2');
  if (!edgeBtn || !elevenBtn || !hint) return;

  const thaiEnabled = selectedLanguageV2 === 'Thai';
  if (!thaiEnabled) {
    selectedTtsSourceV2 = 'edge';
  }

  edgeBtn.disabled = false;
  edgeBtn.classList.toggle('bg-overlay', selectedTtsSourceV2 === 'edge');
  edgeBtn.classList.toggle('text-highlight', selectedTtsSourceV2 === 'edge');
  edgeBtn.classList.toggle('bg-charcoal', selectedTtsSourceV2 !== 'edge');
  edgeBtn.classList.toggle('text-subtext', selectedTtsSourceV2 !== 'edge');

  elevenBtn.disabled = !thaiEnabled;
  elevenBtn.classList.toggle('opacity-50', !thaiEnabled);
  elevenBtn.classList.toggle('cursor-not-allowed', !thaiEnabled);
  elevenBtn.classList.toggle('bg-overlay', thaiEnabled && selectedTtsSourceV2 === 'elevenlabs');
  elevenBtn.classList.toggle('text-highlight', thaiEnabled && selectedTtsSourceV2 === 'elevenlabs');
  elevenBtn.classList.toggle('bg-charcoal', !thaiEnabled || selectedTtsSourceV2 !== 'elevenlabs');
  elevenBtn.classList.toggle('text-subtext', !thaiEnabled || selectedTtsSourceV2 !== 'elevenlabs');

  if (geminiBtn) {
    geminiBtn.disabled = !thaiEnabled;
    geminiBtn.classList.toggle('opacity-50', !thaiEnabled);
    geminiBtn.classList.toggle('cursor-not-allowed', !thaiEnabled);
    geminiBtn.classList.toggle('bg-overlay', thaiEnabled && selectedTtsSourceV2 === 'gemini');
    geminiBtn.classList.toggle('text-highlight', thaiEnabled && selectedTtsSourceV2 === 'gemini');
    geminiBtn.classList.toggle('bg-charcoal', !thaiEnabled || selectedTtsSourceV2 !== 'gemini');
    geminiBtn.classList.toggle('text-subtext', !thaiEnabled || selectedTtsSourceV2 !== 'gemini');
  }

  if (!thaiEnabled) {
    hint.textContent = 'English currently uses Edge only.';
  } else if (selectedTtsSourceV2 === 'elevenlabs') {
    hint.textContent = 'Thai will use ElevenLabs first.';
  } else if (selectedTtsSourceV2 === 'gemini') {
    hint.textContent = 'Thai will use Gemini 2.5 Flash TTS.';
  } else {
    hint.textContent = 'Thai will use Edge directly.';
  }
}

function onGenerationEndV2() {
  isGeneratingV2 = false;
  document.getElementById('topicInputV2').disabled = false;
  document.getElementById('creativeDirectionInputV2').disabled = false;
  document.getElementById('generateBtnV2').disabled = false;
  document.getElementById('resumeBtnV2').disabled = false;
  document.getElementById('cancelBtnV2').classList.add('hidden');
  document.getElementById('scriptInputV2').disabled = false;
  document.getElementById('scriptTitleInputV2').disabled = false;
  document.getElementById('scriptGenerateBtnV2').disabled = false;
  document.getElementById('scriptCancelBtnV2').classList.add('hidden');
  lockModeToggleV2(false);
  document.getElementById('approveBannerV2').classList.add('hidden');
}

// -------------------------------------------------------------------------
// Generate
// -------------------------------------------------------------------------
function handleEventV2(evt) {
  if (evt.type === 'step_start') {
    const i = evt.step;
    if (i >= 0 && i < stepStatesV2.length) {
      stepStatesV2[i].status = 'running';
      stepStatesV2[i].message = '';
      updateStepUIV2(i);
    }
  } else if (evt.type === 'step_done') {
    const i = evt.step;
    if (i >= 0 && i < stepStatesV2.length) {
      stepStatesV2[i].status = 'done';
      updateStepUIV2(i);
      if (i === 0 || i === 3) fetchEpisodeDataV2();
      if (i === 2) {
        shouldLoadVideoPreviewV2 = true;
        fetchEpisodeDataV2();
      }
    }
  } else if (evt.type === 'step_error') {
    const i = evt.step;
    if (i >= 0 && i < stepStatesV2.length) {
      stepStatesV2[i].status = 'error';
      stepStatesV2[i].message = evt.error || 'Error';
      updateStepUIV2(i);
    }
  } else if (evt.type === 'log') {
    const i = typeof evt.step === 'number' ? evt.step : -1;
    if (i >= 0 && i < stepStatesV2.length && stepStatesV2[i].status === 'running') {
      stepStatesV2[i].message = evt.message || '';
      updateStepUIV2(i);
    }
    appendPodcastLogV2(evt.message || '');
  } else if (evt.type === 'waiting_approval') {
    const nextName = evt.next_name || STEP_NAMES_V2[evt.next_step] || 'next step';
    document.getElementById('approveNextLabelV2').textContent = `Next: ${nextName}`;
    document.getElementById('approveBannerV2').classList.remove('hidden');
  } else if (evt.type === 'resume') {
    appendPodcastLogV2(evt.message || 'Resuming pipeline...');
  } else if (evt.type === 'thumbnail_updated') {
    fetchEpisodeDataV2();
  }
}

// -------------------------------------------------------------------------
// Image polling
// -------------------------------------------------------------------------
let renderedImagesV2 = new Set();

function showErrorV2(msg) {
  console.error('Podcast V2 Error: ' + msg);
}

// -------------------------------------------------------------------------
// Publish mode toggle
// -------------------------------------------------------------------------
function onPublishModeChangeV2() {
  const mode = document.querySelector('input[name="publishModeV2"]:checked').value;
  const picker = document.getElementById('schedulePickerV2');
  if (mode === 'schedule') {
    picker.classList.remove('hidden');
    if (!document.getElementById('scheduleDateTimeV2').value) {
      const tomorrow = new Date(Date.now() + 86400000);
      tomorrow.setSeconds(0, 0);
      document.getElementById('scheduleDateTimeV2').value =
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
  renderStepsPanelV2();
  syncTtsSourceUIV2();
  initPodcastSettingsTooltipsV2();
  loadPodcastSettingsV2();
  fetchEpisodeLibraryV2();

  const overlay = document.getElementById('podcastV2DialogOverlay');
  const card = document.getElementById('podcastV2DialogCard');
  const confirmBtn = document.getElementById('podcastV2DialogConfirm');
  const cancelBtn = document.getElementById('podcastV2DialogCancel');
  const closeBtn = document.getElementById('podcastV2DialogClose');
  const settingsOverlay = document.getElementById('podcastV2SettingsOverlay');
  const settingsCard = document.getElementById('podcastV2SettingsCard');
  const settingsCloseBtn = document.getElementById('podcastV2SettingsClose');
  const settingsCancelBtn = document.getElementById('podcastV2SettingsCancel');
  const settingsSaveBtn = document.getElementById('podcastV2SettingsSave');
  const settingsResetBtn = document.getElementById('podcastV2SettingsReset');

  if (overlay && card && confirmBtn && cancelBtn && closeBtn) {
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) closeDialogV2(false);
    });
    card.addEventListener('click', (event) => event.stopPropagation());
    confirmBtn.addEventListener('click', () => closeDialogV2(true));
    cancelBtn.addEventListener('click', () => closeDialogV2(false));
    closeBtn.addEventListener('click', () => closeDialogV2(false));
  }

  if (settingsOverlay && settingsCard && settingsCloseBtn && settingsCancelBtn && settingsSaveBtn && settingsResetBtn) {
    settingsOverlay.addEventListener('click', (event) => {
      if (event.target === settingsOverlay) closePodcastSettingsV2();
    });
    settingsCard.addEventListener('click', (event) => event.stopPropagation());
    settingsCloseBtn.addEventListener('click', closePodcastSettingsV2);
    settingsCancelBtn.addEventListener('click', closePodcastSettingsV2);
    settingsSaveBtn.addEventListener('click', async () => {
      settingsSaveBtn.disabled = true;
      showPodcastSettingsStatusV2('Saving system settings...', 'muted');
      try {
        await savePodcastSettingsV2();
      } finally {
        settingsSaveBtn.disabled = false;
      }
    });
    settingsResetBtn.addEventListener('click', () => {
      resetPodcastSettingsToDefaultsV2();
    });
  }

  document.addEventListener('keydown', (event) => {
    const settingsOpen = !document.getElementById('podcastV2SettingsOverlay')?.classList.contains('hidden');
    const dialogOpen = !document.getElementById('podcastV2DialogOverlay')?.classList.contains('hidden');
    if (!settingsOpen && !dialogOpen) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      if (settingsOpen) closePodcastSettingsV2();
      else closeDialogV2(false);
    }
  });

  document.getElementById('topicInputV2').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startGenerationV2();
  });
});
