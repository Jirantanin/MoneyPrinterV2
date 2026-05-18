function connectEpisodeStreamV2(targetEpisodeId) {
  closePodcastStreamV2();
  podcastEventSourceV2 = new EventSource(`/api/v2/stream/${targetEpisodeId}`);
  podcastEventSourceV2.onmessage = (e) => {
    let evt;
    try { evt = JSON.parse(e.data); } catch { return; }
    handleEventV2(evt);
    if (evt.type === 'complete' || evt.type === 'error' || evt.type === 'cancelled') {
      closePodcastStreamV2();
      stopPollingV2();
      onGenerationEndV2();
      if (evt.type === 'complete') {
        fetchEpisodeDataV2();
      } else if (evt.type === 'cancelled') {
        fetchEpisodeDataV2();
      } else {
        showErrorV2(evt.message || 'Pipeline error. Check server logs.');
        fetchEpisodeDataV2();
      }
    }
  };
  podcastEventSourceV2.onerror = () => {
    // SSE closing after completion/cancel is expected.
  };
}

// -------------------------------------------------------------------------
// Reset UI
// -------------------------------------------------------------------------
async function startGenerationV2() {
  const isScript = document.getElementById('inputModeToggleV2').checked;

  let topic, creativeDirection, rawScript, scriptTitle;
  const visualStyle = document.getElementById('visualStyleSelectV2')?.value || '';
  if (isScript) {
    rawScript = document.getElementById('scriptInputV2').value.trim();
    scriptTitle = document.getElementById('scriptTitleInputV2').value.trim() || 'Custom Script';
    if (!rawScript || isGeneratingV2) return;
  } else {
    topic = document.getElementById('topicInputV2').value.trim();
    creativeDirection = document.getElementById('creativeDirectionInputV2').value.trim();
    if (!topic || isGeneratingV2) return;
  }

  const mode = document.getElementById('modeToggleV2').checked ? 'step' : 'auto';
  const language = selectedLanguageV2;
  const ttsSource = selectedTtsSourceV2;
  const ttsTonePreset = selectedTtsTonePresetV2;

  isGeneratingV2 = true;
  shouldLoadVideoPreviewV2 = true;

  if (isScript) {
    document.getElementById('scriptInputV2').disabled = true;
    document.getElementById('scriptTitleInputV2').disabled = true;
    document.getElementById('scriptGenerateBtnV2').disabled = true;
    document.getElementById('scriptCancelBtnV2').classList.remove('hidden');
  } else {
    document.getElementById('topicInputV2').disabled = true;
    document.getElementById('creativeDirectionInputV2').disabled = true;
    document.getElementById('visualStyleSelectV2').disabled = true;
    document.getElementById('generateBtnV2').disabled = true;
    document.getElementById('cancelBtnV2').classList.remove('hidden');
  }
  lockModeToggleV2(true);
  resetUIV2();

  const systemSettingsPayload = getPodcastSystemSettingsPayloadV2();
  if (visualStyle) {
    if (!systemSettingsPayload.prompting) systemSettingsPayload.prompting = {};
    systemSettingsPayload.prompting.podcast_style_prompt = visualStyle;
  }

  const payload = isScript
    ? { script_mode: true, raw_script: rawScript, title: scriptTitle, visual_style: visualStyle, mode, language, tts_source: ttsSource, tts_tone_preset: ttsTonePreset, system_settings: systemSettingsPayload }
    : { topic, creative_direction: creativeDirection, visual_style: visualStyle, mode, language, tts_source: ttsSource, tts_tone_preset: ttsTonePreset, system_settings: systemSettingsPayload };

  let res;
  try {
    res = await fetch('/api/v2/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    showErrorV2('Failed to connect to server: ' + err.message);
    onGenerationEndV2();
    return;
  }

  const data = await res.json();
  if (data.error) {
    showErrorV2(data.error);
    onGenerationEndV2();
    return;
  }
  episodeIdV2 = data.episode_id;
  connectEpisodeStreamV2(episodeIdV2);
  startImagePollingV2();
}

async function resumeGenerationV2() {
  if (!episodeIdV2 || isGeneratingV2) return;
  const mode = document.getElementById('modeToggleV2').checked ? 'step' : 'auto';

  isGeneratingV2 = true;
  shouldLoadVideoPreviewV2 = true;
  document.getElementById('topicInputV2').disabled = true;
  document.getElementById('creativeDirectionInputV2').disabled = true;
  document.getElementById('visualStyleSelectV2').disabled = true;
  document.getElementById('generateBtnV2').disabled = true;
  document.getElementById('resumeBtnV2').disabled = true;
  document.getElementById('cancelBtnV2').classList.remove('hidden');
  lockModeToggleV2(true);
  stopPollingV2();

  try {
    const res = await fetch(`/api/resume/${episodeIdV2}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        tts_source: selectedTtsSourceV2,
        tts_tone_preset: selectedTtsTonePresetV2,
        system_settings: getPodcastSystemSettingsPayloadV2(),
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Resume failed');
    }
    connectEpisodeStreamV2(episodeIdV2);
    startImagePollingV2();
    appendPodcastLogV2(`Resumed from step ${((data.resumed_from_step ?? 0) + 1)}.`);
  } catch (err) {
    showErrorV2(err.message);
    onGenerationEndV2();
    document.getElementById('resumeBtnV2').disabled = false;
    await fetchEpisodeDataV2();
  }
}

async function redoFromStepV2(stepIndex) {
  if (!episodeIdV2 || isGeneratingV2) return;
  if (!canRedoStepV2(stepIndex)) return;
  const confirmed = await showConfirmV2({
    title: `Redo ${STEP_NAMES_V2[stepIndex]}`,
    message: redoImpactMessageV2(stepIndex),
    confirmLabel: 'Redo Step',
    cancelLabel: 'Keep Current',
    tone: 'warn',
  });
  if (!confirmed) return;

  const mode = document.getElementById('modeToggleV2').checked ? 'step' : 'auto';

  isGeneratingV2 = true;
  shouldLoadVideoPreviewV2 = true;
  document.getElementById('topicInputV2').disabled = true;
  document.getElementById('creativeDirectionInputV2').disabled = true;
  document.getElementById('visualStyleSelectV2').disabled = true;
  document.getElementById('generateBtnV2').disabled = true;
  document.getElementById('resumeBtnV2').disabled = true;
  document.getElementById('cancelBtnV2').classList.remove('hidden');
  lockModeToggleV2(true);
  closePodcastStreamV2();
  stopPollingV2();
  prepareRedoUIV2(stepIndex);

  try {
    const res = await fetch(`/api/redo/${episodeIdV2}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        step: stepIndex,
        mode,
        tts_source: selectedTtsSourceV2,
        tts_tone_preset: selectedTtsTonePresetV2,
        system_settings: getPodcastSystemSettingsPayloadV2(),
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Redo failed');
    }
    connectEpisodeStreamV2(episodeIdV2);
    startImagePollingV2();
    await fetchEpisodeDataV2();
  } catch (err) {
    showErrorV2(err.message);
    onGenerationEndV2();
    await fetchEpisodeDataV2();
  }
}

async function regenSceneAssetV2(sceneIndex) {
  if (!canRegenAssetV2(sceneIndex)) return;
  const confirmed = await showConfirmV2({
    title: `Regenerate Scene ${sceneIndex + 1}`,
    message: `Regenerate image and audio for scene ${sceneIndex + 1}? This will also invalidate render, metadata, and thumbnail outputs.`,
    confirmLabel: 'Regenerate Scene',
    cancelLabel: 'Cancel',
    tone: 'warn',
  });
  if (!confirmed) {
    return;
  }

  regeneratingSceneIndicesV2.add(sceneIndex);
  renderImageGalleryV2();
  appendPodcastLogV2(`Regenerating assets for scene ${sceneIndex + 1}...`);

  try {
    const res = await fetch(`/api/asset/${episodeIdV2}/regen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene_index: sceneIndex,
        system_settings: getPodcastSystemSettingsPayloadV2(),
      }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Scene regen failed');
    }
    if (Array.isArray(data.asset_statuses)) {
      currentAssetStatusesV2 = data.asset_statuses;
      currentSceneCountV2 = Math.max(currentSceneCountV2, currentAssetStatusesV2.length);
    }
    await fetchEpisodeDataV2();
    await fetchEpisodeImagesV2();
  } catch (err) {
    showErrorV2(err.message);
    await fetchEpisodeDataV2();
  } finally {
    regeneratingSceneIndicesV2.delete(sceneIndex);
    renderImageGalleryV2();
  }
}

// -------------------------------------------------------------------------
// Cancel
// -------------------------------------------------------------------------
async function cancelGenerationV2() {
  if (!episodeIdV2) return;
  try {
    await fetch(`/api/cancel/${episodeIdV2}`, { method: 'POST' });
  } catch (_) {}
}

// -------------------------------------------------------------------------
// Approve step (step-by-step mode)
// -------------------------------------------------------------------------
async function approveStepV2() {
  if (!episodeIdV2) return;
  document.getElementById('approveBannerV2').classList.add('hidden');
  document.getElementById('approveBtnV2').disabled = true;
  try {
    await fetch(`/api/approve/${episodeIdV2}`, { method: 'POST' });
  } catch (_) {}
  document.getElementById('approveBtnV2').disabled = false;
}

// -------------------------------------------------------------------------
// SSE event handler
// -------------------------------------------------------------------------
function startImagePollingV2() {
  renderedImagesV2 = new Set();
  pollIntervalV2 = setInterval(async () => {
    if (!episodeIdV2) return;
    try {
      const res = await fetch(`/api/images/${episodeIdV2}`);
      if (res.ok) {
        const data = await res.json();
        renderImageGalleryV2(data.images);
      }
    } catch (_) {}
  }, 2000);
}

function stopPollingV2() {
  if (pollIntervalV2) {
    clearInterval(pollIntervalV2);
    pollIntervalV2 = null;
  }
  if (episodeIdV2) {
    setTimeout(async () => {
      try {
        const res = await fetch(`/api/images/${episodeIdV2}`);
        if (res.ok) { const d = await res.json(); renderImageGalleryV2(d.images); }
      } catch (_) {}
    }, 1000);
  }
}

async function fetchEpisodeImagesV2() {
  if (!episodeIdV2) return;
  try {
    const res = await fetch(`/api/images/${episodeIdV2}`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.asset_statuses)) {
        currentAssetStatusesV2 = data.asset_statuses;
        currentSceneCountV2 = Math.max(currentSceneCountV2, currentAssetStatusesV2.length);
      }
      renderImageGalleryV2(data.images);
    }
  } catch (_) {}
}

async function fetchEpisodeDataV2() {
  if (!episodeIdV2) return;
  try {
    const res = await fetch(`/api/episode/${episodeIdV2}`);
    if (!res.ok) return;
    const data = await res.json();
    applyEpisodeStateV2({ ...data, episode_id: episodeIdV2 });
  } catch (_) {}
}

async function copyMetadataFieldV2(field) {
  const metadata = currentMetadataV2 || {};
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
    document.getElementById('thumbnailStudioStatusV2').textContent = 'Metadata copied to clipboard';
  } catch (_) {
    document.getElementById('thumbnailStudioStatusV2').textContent = 'Copy failed';
  }
}

async function uploadReplacementThumbnailV2() {
  if (!episodeIdV2) return;
  const input = document.getElementById('thumbnailFileInputV2');
  const statusEl = document.getElementById('thumbnailUploadStatusV2');
  const button = document.getElementById('thumbnailUploadBtnV2');
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
    const res = await fetch(`/api/thumbnail/${episodeIdV2}`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Upload failed');
    }
    renderThumbnailStudioV2({
      headline: document.getElementById('thumbHeadlineV2').textContent,
      supporting_text: document.getElementById('thumbSupportV2').textContent,
      canva_prompt: document.getElementById('thumbPromptV2').textContent,
      gen_prompt: document.getElementById('thumbGenPromptV2').textContent,
    }, data.thumbnail_url);
    statusEl.className = 'text-xs text-accent';
    statusEl.textContent = 'Replacement thumbnail uploaded. This will be used on YouTube.';
    document.getElementById('thumbnailStudioStatusV2').textContent = 'Custom thumbnail loaded';
  } catch (err) {
    statusEl.className = 'text-xs text-rose';
    statusEl.textContent = err.message;
  } finally {
    button.disabled = false;
  }
}

async function fetchEpisodeLibraryV2() {
  try {
    const res = await fetch('/api/episodes');
    const data = await res.json();
    const episodes = data.episodes || [];
    renderEpisodeLibraryV2(episodes);
    hasAutoLoadedEpisodeV2 = true;
  } catch (_) {
    document.getElementById('episodeLibraryV2').innerHTML =
      '<p class="text-sm text-rose">Failed to load saved episodes.</p>';
  }
}

async function loadEpisodeV2(targetEpisodeId, loadVideo = true) {
  try {
    resetUIV2();
    renderedImagesV2 = new Set();
    const loadRes = await fetch(`/api/load/${targetEpisodeId}`, { method: 'POST' });
    const loadData = await loadRes.json();
    if (!loadRes.ok || loadData.error) {
      throw new Error(loadData.error || 'Load failed');
    }
    episodeIdV2 = targetEpisodeId;
    shouldLoadVideoPreviewV2 = loadVideo;
    await fetchEpisodeDataV2();
  } catch (err) {
    showErrorV2(err.message);
  }
}

async function markAsUploadedV2() {
  if (!episodeIdV2) return;
  const btn = document.getElementById('markUploadedBtnV2');
  const statusEl = document.getElementById('markUploadedStatusV2');
  btn.disabled = true;
  statusEl.textContent = 'Marking...';
  try {
    const res = await fetch(`/api/mark-uploaded/${episodeIdV2}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      btn.textContent = 'Uploaded ✓';
      btn.classList.remove('bg-emerald-600');
      btn.classList.add('bg-gray-600');
      statusEl.textContent = `Marked at ${new Date(data.uploaded_at).toLocaleString()}`;
      currentEpisodeStatusV2 = 'uploaded';
      isCurrentEpisodeUploadedV2 = true;
      await fetchEpisodeDataV2();
      await fetchEpisodeLibraryV2();
    } else {
      btn.disabled = false;
      statusEl.textContent = data.error || 'Failed';
    }
  } catch (e) {
    btn.disabled = false;
    statusEl.textContent = 'Network error';
  }
}
