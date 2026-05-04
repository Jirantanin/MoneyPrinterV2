function connectEpisodeStream(targetEpisodeId) {
  closePodcastStream();
  podcastEventSource = new EventSource(`/api/stream/${targetEpisodeId}`);
  podcastEventSource.onmessage = (e) => {
    let evt;
    try { evt = JSON.parse(e.data); } catch { return; }
    handleEvent(evt);
    if (evt.type === 'complete' || evt.type === 'error' || evt.type === 'cancelled') {
      closePodcastStream();
      stopPolling();
      onGenerationEnd();
      if (evt.type === 'complete') {
        const uploadBtnEl = document.getElementById('uploadBtn');
        if (uploadBtnEl) uploadBtnEl.disabled = false;
        fetchEpisodeData();
      } else if (evt.type === 'cancelled') {
        const statusEl = document.getElementById('uploadStatus');
        if (statusEl) {
          statusEl.className = 'text-sm text-subtext';
          statusEl.textContent = 'Generation cancelled.';
        }
        fetchEpisodeData();
      } else {
        showError(evt.message || 'Pipeline error. Check server logs.');
        fetchEpisodeData();
      }
    }
  };
  podcastEventSource.onerror = () => {
    // SSE closing after completion/cancel is expected.
  };
}

// -------------------------------------------------------------------------
// Reset UI
// -------------------------------------------------------------------------
async function startGeneration() {
  const isScript = document.getElementById('inputModeToggle').checked;

  let topic, creativeDirection, rawScript, scriptTitle, visualStyle;
  if (isScript) {
    rawScript = document.getElementById('scriptInput').value.trim();
    scriptTitle = document.getElementById('scriptTitleInput').value.trim() || 'Custom Script';
    if (!rawScript || isGenerating) return;
  } else {
    topic = document.getElementById('topicInput').value.trim();
    creativeDirection = document.getElementById('creativeDirectionInput').value.trim();
    visualStyle = document.getElementById('visualStyleSelect').value;
    if (!topic || isGenerating) return;
  }

  const mode = document.getElementById('modeToggle').checked ? 'step' : 'auto';
  const language = selectedLanguage;
  const ttsSource = selectedTtsSource;

  isGenerating = true;
  shouldLoadVideoPreview = true;

  if (isScript) {
    document.getElementById('scriptInput').disabled = true;
    document.getElementById('scriptTitleInput').disabled = true;
    document.getElementById('scriptGenerateBtn').disabled = true;
    document.getElementById('scriptCancelBtn').classList.remove('hidden');
  } else {
    document.getElementById('topicInput').disabled = true;
    document.getElementById('creativeDirectionInput').disabled = true;
    document.getElementById('visualStyleSelect').disabled = true;
    document.getElementById('generateBtn').disabled = true;
    document.getElementById('cancelBtn').classList.remove('hidden');
  }
  lockModeToggle(true);
  resetUI();

  const systemSettingsPayload = getPodcastSystemSettingsPayload();
  if (visualStyle) {
    if (!systemSettingsPayload.prompting) systemSettingsPayload.prompting = {};
    systemSettingsPayload.prompting.podcast_style_prompt = visualStyle;
  }

  const payload = isScript
    ? { script_mode: true, raw_script: rawScript, title: scriptTitle, mode, language, tts_source: ttsSource, system_settings: systemSettingsPayload }
    : { topic, creative_direction: creativeDirection, visual_style: visualStyle, mode, language, tts_source: ttsSource, system_settings: systemSettingsPayload };

  let res;
  try {
    res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    showError('Failed to connect to server: ' + err.message);
    onGenerationEnd();
    return;
  }

  const data = await res.json();
  if (data.error) {
    showError(data.error);
    onGenerationEnd();
    return;
  }
  episodeId = data.episode_id;
  connectEpisodeStream(episodeId);
  startImagePolling();
}

async function resumeGeneration() {
  if (!episodeId || isGenerating) return;
  const mode = document.getElementById('modeToggle').checked ? 'step' : 'auto';

  isGenerating = true;
  shouldLoadVideoPreview = true;
  document.getElementById('topicInput').disabled = true;
  document.getElementById('creativeDirectionInput').disabled = true;
  document.getElementById('visualStyleSelect').disabled = true;
  document.getElementById('generateBtn').disabled = true;
  document.getElementById('resumeBtn').disabled = true;
  document.getElementById('cancelBtn').classList.remove('hidden');
  lockModeToggle(true);
  stopPolling();

  try {
    const res = await fetch(`/api/resume/${episodeId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        tts_source: selectedTtsSource,
        system_settings: getPodcastSystemSettingsPayload(),
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Resume failed');
    }
    connectEpisodeStream(episodeId);
    startImagePolling();
    appendPodcastLog(`Resumed from step ${((data.resumed_from_step ?? 0) + 1)}.`);
  } catch (err) {
    showError(err.message);
    onGenerationEnd();
    document.getElementById('resumeBtn').disabled = false;
    await fetchEpisodeData();
  }
}

async function redoFromStep(stepIndex) {
  if (!episodeId || isGenerating) return;
  if (!canRedoStep(stepIndex)) return;
  const confirmed = await showConfirm({
    title: `Redo ${STEP_NAMES[stepIndex]}`,
    message: redoImpactMessage(stepIndex),
    confirmLabel: 'Redo Step',
    cancelLabel: 'Keep Current',
    tone: 'warn',
  });
  if (!confirmed) return;

  const mode = document.getElementById('modeToggle').checked ? 'step' : 'auto';

  isGenerating = true;
  shouldLoadVideoPreview = true;
  document.getElementById('topicInput').disabled = true;
  document.getElementById('creativeDirectionInput').disabled = true;
  document.getElementById('visualStyleSelect').disabled = true;
  document.getElementById('generateBtn').disabled = true;
  document.getElementById('resumeBtn').disabled = true;
  document.getElementById('cancelBtn').classList.remove('hidden');
  lockModeToggle(true);
  closePodcastStream();
  stopPolling();
  prepareRedoUI(stepIndex);

  try {
    const res = await fetch(`/api/redo/${episodeId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        step: stepIndex,
        mode,
        tts_source: selectedTtsSource,
        system_settings: getPodcastSystemSettingsPayload(),
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Redo failed');
    }
    connectEpisodeStream(episodeId);
    startImagePolling();
    await fetchEpisodeData();
  } catch (err) {
    showError(err.message);
    onGenerationEnd();
    await fetchEpisodeData();
  }
}

async function regenSceneAsset(sceneIndex) {
  if (!canRegenAsset(sceneIndex)) return;
  const confirmed = await showConfirm({
    title: `Regenerate Scene ${sceneIndex + 1}`,
    message: `Regenerate image and audio for scene ${sceneIndex + 1}? This will also invalidate render, metadata, and thumbnail outputs.`,
    confirmLabel: 'Regenerate Scene',
    cancelLabel: 'Cancel',
    tone: 'warn',
  });
  if (!confirmed) {
    return;
  }

  regeneratingSceneIndices.add(sceneIndex);
  renderImageGallery();
  appendPodcastLog(`Regenerating assets for scene ${sceneIndex + 1}...`);

  try {
    const res = await fetch(`/api/asset/${episodeId}/regen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene_index: sceneIndex,
        system_settings: getPodcastSystemSettingsPayload(),
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Scene regen failed');
    }
    if (Array.isArray(data.asset_statuses)) {
      currentAssetStatuses = data.asset_statuses;
      currentSceneCount = Math.max(currentSceneCount, currentAssetStatuses.length);
    }
    await fetchEpisodeData();
    await fetchEpisodeImages();
  } catch (err) {
    showError(err.message);
    await fetchEpisodeData();
  } finally {
    regeneratingSceneIndices.delete(sceneIndex);
    renderImageGallery();
  }
}

function legacyEpisodeStreamHandlerDeprecated() {
  const evtSource = new EventSource(`/api/stream/${episodeId}`);
  evtSource.onmessage = (e) => {
    let evt;
    try { evt = JSON.parse(e.data); } catch { return; }
    handleEvent(evt);
    if (evt.type === 'complete' || evt.type === 'error' || evt.type === 'cancelled') {
      evtSource.close();
      stopPolling();
      onGenerationEnd();
      if (evt.type === 'complete') {
        const uploadBtnEl = document.getElementById('uploadBtn');
        if (uploadBtnEl) uploadBtnEl.disabled = false;
        fetchEpisodeData();
      } else if (evt.type === 'cancelled') {
        const statusEl = document.getElementById('uploadStatus');
        if (statusEl) {
          statusEl.className = 'text-sm text-subtext';
          statusEl.textContent = 'Generation cancelled.';
        }
      } else {
        showError(evt.message || 'Pipeline error. Check server logs.');
      }
    }
  };
  evtSource.onerror = () => {
    // SSE closed by server after pipeline ends โ€” this is normal
  };

  // Start image polling
  startImagePolling();
}

// -------------------------------------------------------------------------
// Cancel
// -------------------------------------------------------------------------
async function cancelGeneration() {
  if (!episodeId) return;
  try {
    await fetch(`/api/cancel/${episodeId}`, { method: 'POST' });
  } catch (_) {}
}

// -------------------------------------------------------------------------
// Approve step (step-by-step mode)
// -------------------------------------------------------------------------
async function approveStep() {
  if (!episodeId) return;
  document.getElementById('approveBanner').classList.add('hidden');
  document.getElementById('approveBtn').disabled = true;
  try {
    await fetch(`/api/approve/${episodeId}`, { method: 'POST' });
  } catch (_) {}
  document.getElementById('approveBtn').disabled = false;
}

// -------------------------------------------------------------------------
// SSE event handler
// -------------------------------------------------------------------------
function startImagePolling() {
  renderedImages = new Set();
  pollInterval = setInterval(async () => {
    if (!episodeId) return;
    try {
      const res = await fetch(`/api/images/${episodeId}`);
      if (res.ok) {
        const data = await res.json();
        renderImageGallery(data.images);
      }
    } catch (_) {}
  }, 2000);
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  // One final poll to catch last images
  if (episodeId) {
    setTimeout(async () => {
      try {
        const res = await fetch(`/api/images/${episodeId}`);
        if (res.ok) { const d = await res.json(); renderImageGallery(d.images); }
      } catch (_) {}
    }, 1000);
  }
}

async function fetchEpisodeImages() {
  if (!episodeId) return;
  try {
    const res = await fetch(`/api/images/${episodeId}`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.asset_statuses)) {
        currentAssetStatuses = data.asset_statuses;
        currentSceneCount = Math.max(currentSceneCount, currentAssetStatuses.length);
      }
      renderImageGallery(data.images);
    }
  } catch (_) {}
}

async function fetchEpisodeData() {
  if (!episodeId) return;
  try {
    const res = await fetch(`/api/episode/${episodeId}`);
    if (!res.ok) return;
    const data = await res.json();
    applyEpisodeState({ ...data, episode_id: episodeId });
  } catch (_) {}
}

async function copyMetadataField(field) {
  const metadata = currentMetadata || {};
  let text = '';

  if (field === 'title') text = metadata.title || '';
  else if (field === 'description') text = metadata.description || '';
  else if (field === 'tags') text = Array.isArray(metadata.tags) ? metadata.tags.join(', ') : '';
  else if (field === 'all') {
    const parts = [];
    if (metadata.title) parts.push(`Title: ${metadata.title}`);
    if (metadata.description) parts.push(`Description:\n${metadata.description}`);
    if (Array.isArray(metadata.tags) && metadata.tags.length) parts.push(`Tags: ${metadata.tags.join(', ')}`);
    text = parts.join('\n\n');
  }

  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    document.getElementById('thumbnailStudioStatus').textContent = 'Metadata copied to clipboard';
  } catch (_) {
    document.getElementById('thumbnailStudioStatus').textContent = 'Copy failed';
  }
}

async function uploadReplacementThumbnail() {
  if (!episodeId) return;
  const input = document.getElementById('thumbnailFileInput');
  const statusEl = document.getElementById('thumbnailUploadStatus');
  const button = document.getElementById('thumbnailUploadBtn');
  const file = input.files?.[0];

  if (!file) {
    statusEl.className = 'text-xs text-rose';
    statusEl.textContent = 'Choose an image first.';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  button.disabled = true;
  statusEl.className = 'text-xs text-subtext';
  statusEl.textContent = 'Uploading replacement thumbnail...';

  try {
    const res = await fetch(`/api/thumbnail/${episodeId}`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Upload failed');
    }
    renderThumbnailStudio({
      headline: document.getElementById('thumbHeadline').textContent,
      supporting_text: document.getElementById('thumbSupport').textContent,
      canva_prompt: document.getElementById('thumbPrompt').textContent,
      gen_prompt: document.getElementById('thumbGenPrompt').textContent,
    }, data.thumbnail_url);
    statusEl.className = 'text-xs text-accent';
    statusEl.textContent = 'Replacement thumbnail uploaded. This will be used on YouTube.';
    document.getElementById('thumbnailStudioStatus').textContent = 'Custom thumbnail loaded';
  } catch (err) {
    statusEl.className = 'text-xs text-rose';
    statusEl.textContent = err.message;
  } finally {
    button.disabled = false;
  }
}

async function fetchEpisodeLibrary() {
  try {
    const res = await fetch('/api/episodes');
    const data = await res.json();
    const episodes = data.episodes || [];
    renderEpisodeLibrary(episodes);
    hasAutoLoadedEpisode = true; // Always start with a blank form — user opens episodes manually
  } catch (_) {
    document.getElementById('episodeLibrary').innerHTML =
      '<p class="text-sm text-rose">Failed to load saved episodes.</p>';
  }
}

async function loadEpisode(targetEpisodeId, loadVideo = true) {
  try {
    resetUI();
    renderedImages = new Set();
    const loadRes = await fetch(`/api/load/${targetEpisodeId}`, { method: 'POST' });
    const loadData = await loadRes.json();
    if (!loadRes.ok || loadData.error) {
      throw new Error(loadData.error || 'Load failed');
    }
    episodeId = targetEpisodeId;
    shouldLoadVideoPreview = loadVideo;
    await fetchEpisodeData();
    const loadStatusEl = document.getElementById('uploadStatus');
    if (loadStatusEl) {
      loadStatusEl.className = 'text-sm text-subtext';
      loadStatusEl.textContent = `Loaded saved episode: ${targetEpisodeId}`;
    }
  } catch (err) {
    showError(err.message);
  }
}

async function uploadToYouTube() {
  // uploadBtn/uploadStatus were removed from DOM (manual upload flow).
  // This function is kept for potential future use but is not reachable via UI.
  const uploadBtnEl = document.getElementById('uploadBtn');
  const statusEl = document.getElementById('uploadStatus');
  if (!uploadBtnEl && !statusEl) {
    console.warn('uploadToYouTube: legacy upload UI not present');
    return;
  }
  if (!episodeId) return;
  if (isCurrentEpisodeUploaded) {
    if (statusEl) {
      statusEl.className = 'text-sm text-subtext';
      statusEl.textContent = 'This episode is already uploaded. Open it as history only.';
    }
    return;
  }
  if (uploadBtnEl) uploadBtnEl.disabled = true;
  if (statusEl) statusEl.className = 'text-sm text-subtext';

  const mode = document.querySelector('input[name="publishMode"]:checked').value;
  let body = { privacy_status: 'public' };

  if (mode === 'schedule') {
    const localVal = document.getElementById('scheduleDateTime').value;
    if (!localVal) {
      showError('Please pick a date and time to schedule.');
      if (uploadBtnEl) uploadBtnEl.disabled = false;
      return;
    }
    // Convert local datetime-local value to UTC ISO string
    const publishAt = new Date(localVal).toISOString();
    const now = new Date();
    if (new Date(localVal) <= now) {
      showError('Scheduled time must be in the future.');
      if (uploadBtnEl) uploadBtnEl.disabled = false;
      return;
    }
    body = { privacy_status: 'private', publish_at: publishAt };
    if (statusEl) statusEl.textContent = 'Uploading (scheduled)...';
  } else {
    if (statusEl) statusEl.textContent = 'Uploading...';
  }

  try {
    const res = await fetch(`/api/upload/${episodeId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data.video_url) {
      if (data.scheduled && data.publish_at) {
        const localTime = new Date(data.publish_at).toLocaleString();
        if (statusEl) statusEl.innerHTML =
          'Scheduled for ' + localTime + ' โ€” ' +
          '<a href="' + data.video_url + '" target="_blank" class="text-sky underline">View on YouTube</a>';
      } else {
        if (statusEl) statusEl.innerHTML =
          'Uploaded: <a href="' + data.video_url + '" target="_blank" class="text-sky underline">' +
          data.video_url + '</a>';
      }
      if (statusEl) statusEl.className = 'text-sm text-accent';
    } else {
      showError(data.error || 'Upload failed');
      if (uploadBtnEl) uploadBtnEl.disabled = false;
    }
  } catch (err) {
    showError('Upload request failed: ' + err.message);
    if (uploadBtnEl) uploadBtnEl.disabled = false;
  }
}

async function markAsUploaded() {
  if (!episodeId) return;
  const btn = document.getElementById('markUploadedBtn');
  const statusEl = document.getElementById('markUploadedStatus');
  btn.disabled = true;
  statusEl.textContent = 'Marking...';
  try {
    const res = await fetch(`/api/mark-uploaded/${episodeId}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      btn.textContent = 'Uploaded โ“';
      btn.classList.remove('bg-emerald-600');
      btn.classList.add('bg-gray-600');
      statusEl.textContent = `Marked at ${new Date(data.uploaded_at).toLocaleString()}`;
      currentEpisodeStatus = 'uploaded';
      isCurrentEpisodeUploaded = true;
      await fetchEpisodeData();
      await fetchEpisodeLibrary();
    } else {
      btn.disabled = false;
      statusEl.textContent = data.error || 'Failed';
    }
  } catch (e) {
    btn.disabled = false;
    statusEl.textContent = 'Network error';
  }
}

// -------------------------------------------------------------------------
// Init on load
// -------------------------------------------------------------------------
