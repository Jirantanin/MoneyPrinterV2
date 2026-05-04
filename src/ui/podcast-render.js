function renderStepsPanel() {
  const panel = document.getElementById('stepsPanel');
  panel.innerHTML = '';
  stepStates.forEach((step, i) => {
    const row = document.createElement('div');
    row.id = `step-row-${i}`;
    row.className = 'state-row ' +
      (step.status === 'running' ? 'is-running' : step.status === 'done' ? 'is-done' : step.status === 'error' ? 'is-error' : '');

    // Icon
    const iconWrap = document.createElement('div');
    iconWrap.id = `step-icon-${i}`;
    iconWrap.className = 'state-icon';
    iconWrap.innerHTML = iconForStatus(step.status);

    // Text block
    const textBlock = document.createElement('div');
    textBlock.className = 'flex-1 min-w-0';

    const nameEl = document.createElement('div');
    nameEl.className = colorForStatus(step.status);
    nameEl.textContent = `${i + 1}. ${step.name}`;

    const msgEl = document.createElement('div');
    msgEl.id = `step-msg-${i}`;
    msgEl.className = 'state-message truncate';
    msgEl.textContent = step.message || '';

    textBlock.appendChild(nameEl);
    textBlock.appendChild(msgEl);

    const actionsWrap = document.createElement('div');
    actionsWrap.id = `step-actions-${i}`;
    actionsWrap.className = 'shrink-0 flex items-center gap-2';
    renderStepActions(actionsWrap, i);

    row.appendChild(iconWrap);
    row.appendChild(textBlock);
    row.appendChild(actionsWrap);
    panel.appendChild(row);
  });
}

function iconForStatus(status) {
  switch (status) {
    case 'pending': return '<span class="text-overlay text-base leading-none">&#9711;</span>';
    case 'running': return '<div class="step-spinner"></div>';
    case 'done':    return '<span class="text-accent text-base leading-none font-bold">&#10003;</span>';
    case 'error':   return '<span class="text-rose text-base leading-none font-bold">&#10007;</span>';
    default:        return '';
  }
}

function colorForStatus(status) {
  switch (status) {
    case 'running': return 'state-name state-running';
    case 'done':    return 'state-name state-done';
    case 'error':   return 'state-name state-error';
    default:        return 'state-name state-pending';
  }
}

function updateStepUI(index) {
  const step = stepStates[index];
  const row = document.getElementById(`step-row-${index}`);
  const icon = document.getElementById(`step-icon-${index}`);
  const msg = document.getElementById(`step-msg-${index}`);
  const actions = document.getElementById(`step-actions-${index}`);

  if (!row || !icon || !msg) return;

  // Update row highlight
  row.className = 'state-row ' +
    (step.status === 'running' ? 'is-running' : step.status === 'done' ? 'is-done' : step.status === 'error' ? 'is-error' : '');

  // Update icon
  icon.innerHTML = iconForStatus(step.status);

  // Update name color
  const nameEl = row.querySelector('div.flex-1 > div:first-child');
  if (nameEl) nameEl.className = colorForStatus(step.status);

  // Update message
  msg.textContent = step.message || '';
  if (actions) renderStepActions(actions, index);
}

function canRedoStep(stepIndex) {
  if (!episodeId || isGenerating || currentEpisodeStatus === 'running' || isCurrentEpisodeUploaded) return false;
  if (stepIndex < 0 || stepIndex >= stepStates.length) return false;
  if (currentEpisodeStatus === 'uploaded') return false;
  const nextIncomplete = stepStates.findIndex(step => step.status !== 'done');
  if (nextIncomplete === -1) return true;
  return stepIndex <= nextIncomplete || stepStates[stepIndex].status === 'done' || stepStates[stepIndex].status === 'error';
}

function redoImpactMessage(stepIndex) {
  switch (stepIndex) {
    case 0:
      return 'Redo from Generate Script will discard script, assets, render, metadata, and thumbnail outputs.';
    case 1:
      return 'Redo from Generate Assets will discard assets, render, metadata, and thumbnail outputs.';
    case 2:
      return 'Redo from Render Video will discard render, metadata, and thumbnail outputs.';
    case 3:
      return 'Redo from Generate Metadata will discard metadata and thumbnail outputs.';
    case 4:
      return 'Redo from Generate Thumbnail will replace the current thumbnail.';
    default:
      return 'Redo from this step will discard downstream outputs.';
  }
}

function renderStepActions(container, stepIndex) {
  container.innerHTML = '';
  if (!canRedoStep(stepIndex)) return;

  const redoBtn = document.createElement('button');
  redoBtn.type = 'button';
  redoBtn.className = 'glass-link text-[11px] text-yellow-300 hover:underline';
  redoBtn.textContent = 'Redo from here';
  redoBtn.onclick = () => redoFromStep(stepIndex);
  container.appendChild(redoBtn);
}

function renderPodcastLogs() {
  const logEl = document.getElementById('podcastLogOutput');
  if (!logEl) return;
  if (!podcastLogs.length) {
    logEl.textContent = 'Logs will appear here.';
    return;
  }
  logEl.textContent = podcastLogs.join('\n');
  logEl.scrollTop = logEl.scrollHeight;
}

function appendPodcastLog(message) {
  const text = (message || '').trim();
  if (!text) return;
  podcastLogs.push(text);
  if (podcastLogs.length > 500) {
    podcastLogs = podcastLogs.slice(-500);
  }
  renderPodcastLogs();
}

function setPodcastLogs(logs) {
  podcastLogs = Array.isArray(logs) ? logs.slice(-500) : [];
  renderPodcastLogs();
}

function clearPodcastLogs() {
  podcastLogs = [];
  renderPodcastLogs();
}

function clearMetadataView() {
  document.getElementById('metadataPanel').classList.add('hidden');
  document.getElementById('metadataActions').classList.add('hidden');
  document.getElementById('metadataContent').innerHTML = '';
  currentMetadata = {};
}

function clearThumbnailStudio() {
  document.getElementById('thumbnailStudio').classList.add('hidden');
  document.getElementById('thumbHeadline').textContent = '';
  document.getElementById('thumbSupport').textContent = '';
  document.getElementById('thumbPrompt').textContent = '';
  document.getElementById('thumbGenPrompt').textContent = '';
  document.getElementById('thumbnailStudioStatus').textContent = '';
  document.getElementById('thumbnailUploadStatus').textContent = '';
  document.getElementById('thumbnailFileInput').value = '';
  document.getElementById('thumbnailPreview').src = '';
  document.getElementById('thumbnailPreviewWrap').classList.add('hidden');
  document.getElementById('thumbnailPreview').classList.add('hidden');
  const thumbPlaceholder = document.getElementById('thumbnailPreviewPlaceholder');
  if (thumbPlaceholder) thumbPlaceholder.classList.remove('hidden');
}

function hideManualUploadRow() {
  const manualRow = document.getElementById('manualUploadRow');
  if (manualRow) {
    manualRow.classList.add('hidden');
    manualRow.classList.remove('flex');
  }
}

function prepareRedoUI(stepIndex) {
  for (let i = stepIndex; i < stepStates.length; i++) {
    stepStates[i].status = 'pending';
    stepStates[i].message = '';
  }
  renderStepsPanel();

  if (stepIndex <= 1) {
    renderedImages = new Set();
    currentAssetStatuses = [];
    currentSceneCount = stepIndex <= 0 ? 0 : currentSceneCount;
    renderImageGallery();
  }
  if (stepIndex <= 0) {
    document.getElementById('scriptPanel').innerHTML =
      '<p id="noScriptMsg" class="text-subtext text-sm">Script will appear after generation begins.</p>';
  }
  if (stepIndex <= 3) {
    clearMetadataView();
  }
  if (stepIndex <= 4) {
    clearThumbnailStudio();
  }
  hideManualUploadRow();
  currentEpisodeStatus = 'idle';
  isCurrentEpisodeUploaded = false;
}

function renderVideoPreview(videoUrl) {
  const player = document.getElementById('videoPreviewPlayer');
  const skeleton = document.getElementById('videoPreviewSkeleton');
  const status = document.getElementById('videoPreviewStatus');

  if (videoUrl) {
    player.src = videoUrl;
    player.classList.remove('hidden');
    skeleton.classList.add('hidden');
    status.textContent = 'Preview ready';
  } else {
    player.pause();
    player.removeAttribute('src');
    player.load();
    player.classList.add('hidden');
    skeleton.classList.remove('hidden');
    status.textContent = 'Waiting for render';
  }
}

function canRegenAsset(sceneIndex) {
  return !!episodeId && !isGenerating && currentEpisodeStatus !== 'running' && !isCurrentEpisodeUploaded && !regeneratingSceneIndices.has(sceneIndex);
}

function renderImageGallery(images) {
  const gallery = document.getElementById('imageGallery');
  const sceneCount = currentSceneCount || currentAssetStatuses.length;
  if (!sceneCount) {
    gallery.innerHTML = '<div id="noImagesMsg" class="col-span-3 flex items-center justify-center text-subtext text-sm h-32">No images yet</div>';
    return;
  }

  const imageSet = new Set((images || []).filter(name => /^scene_\d+\.png$/.test(name)));
  const statusMap = new Map(
    (currentAssetStatuses || []).map(status => [status.scene_index, status])
  );

  gallery.innerHTML = '';
  for (let i = 0; i < sceneCount; i++) {
    const sceneNum = String(i).padStart(2, '0');
    const filename = `scene_${sceneNum}.png`;
    const status = statusMap.get(i) || {};
    const imageExists = status.image_exists || imageSet.has(filename);
    const audioExists = !!status.audio_exists;
    const imageUrl = status.image_url || (imageExists ? `/static/${episodeId}/${filename}` : '');

    const card = document.createElement('div');
    card.className = 'relative aspect-video rounded-2xl overflow-hidden border border-overlay bg-charcoal';

    const topBar = document.createElement('div');
    topBar.className = 'absolute inset-x-0 top-0 z-10 flex items-center justify-between p-2';

    const label = document.createElement('span');
    label.className = 'state-pill text-[10px] uppercase tracking-[0.18em]';
    label.textContent = `Scene ${i + 1}`;

    const regenBtn = document.createElement('button');
    regenBtn.type = 'button';
    regenBtn.className = 'glass-link text-[10px]';
    regenBtn.textContent = regeneratingSceneIndices.has(i) ? 'Regen...' : 'Regen';
    regenBtn.disabled = !canRegenAsset(i);
    regenBtn.onclick = () => regenSceneAsset(i);

    topBar.appendChild(label);
    topBar.appendChild(regenBtn);
    card.appendChild(topBar);

    if (imageExists) {
      const link = document.createElement('a');
      link.href = imageUrl;
      link.target = '_blank';
      link.className = 'block w-full h-full image-card';

      const img = document.createElement('img');
      img.src = imageUrl;
      img.alt = filename;
      img.className = 'w-full h-full object-cover';
      img.loading = 'lazy';

      link.appendChild(img);
      card.appendChild(link);
    } else {
      const placeholder = document.createElement('div');
      placeholder.className = 'w-full h-full flex items-center justify-center text-subtext text-xs px-4 text-center';
      placeholder.textContent = 'No image yet';
      card.appendChild(placeholder);
    }

    const footer = document.createElement('div');
    footer.className = 'absolute inset-x-0 bottom-0 z-10 px-2 py-1.5 text-[11px] bg-black/45 text-subtext';
    footer.textContent = imageExists && audioExists
      ? 'Image + audio ready'
      : imageExists
        ? 'Image ready, audio missing'
        : audioExists
          ? 'Audio ready, image missing'
          : 'Image + audio missing';
    card.appendChild(footer);

    gallery.appendChild(card);
  }
}

// -------------------------------------------------------------------------
// Episode data fetch (script + metadata)
// -------------------------------------------------------------------------
function renderScript(scenes) {
  const panel = document.getElementById('scriptPanel');
  // Remove placeholder
  const placeholder = document.getElementById('noScriptMsg');
  if (placeholder) placeholder.remove();

  // Build scene list โ€” skip already-rendered items by count
  const existing = panel.querySelectorAll('.scene-item').length;
  scenes.slice(existing).forEach((narration, idx) => {
    const sceneNum = existing + idx + 1;
    const item = document.createElement('div');
    item.className = 'scene-item fade-in state-row px-4 py-3';

    const num = document.createElement('span');
    num.className = 'text-xs font-semibold tracking-[0.18em] uppercase text-sky mr-2';
    num.textContent = `Scene ${sceneNum}:`;

    const text = document.createElement('span');
    text.className = 'text-sm text-text';
    text.textContent = ' ' + narration;

    item.appendChild(num);
    item.appendChild(text);
    panel.appendChild(item);
  });
}

function renderMetadata(metadata) {
  const panel = document.getElementById('metadataPanel');
  const actions = document.getElementById('metadataActions');
  const content = document.getElementById('metadataContent');
  panel.classList.remove('hidden');
  actions.classList.remove('hidden');
  content.innerHTML = '';
  currentMetadata = metadata || {};

  // Title
  if (metadata.title) {
    const titleEl = document.createElement('p');
    titleEl.className = 'text-[1.12rem] font-semibold text-text leading-snug tracking-[-0.025em]';
    titleEl.textContent = metadata.title;
    content.appendChild(titleEl);
  }

  // Description
  if (metadata.description) {
    const descEl = document.createElement('p');
    descEl.className = 'text-sm text-subtext whitespace-pre-wrap leading-relaxed';
    descEl.textContent = metadata.description;
    content.appendChild(descEl);
  }

  // Tags
  if (metadata.tags && metadata.tags.length > 0) {
    const tagsWrap = document.createElement('div');
    tagsWrap.className = 'flex flex-wrap gap-2 pt-1';
    metadata.tags.forEach(tag => {
      const badge = document.createElement('span');
      badge.className = 'state-pill text-xs';
      badge.textContent = tag;
      tagsWrap.appendChild(badge);
    });
    content.appendChild(tagsWrap);
  }
}

function renderThumbnailStudio(promptPack, thumbnailUrl) {
  const panel = document.getElementById('thumbnailStudio');
  panel.classList.remove('hidden');

  document.getElementById('thumbHeadline').textContent = promptPack?.headline || '';
  document.getElementById('thumbSupport').textContent = promptPack?.supporting_text || '';
  document.getElementById('thumbPrompt').textContent = promptPack?.canva_prompt || '';
  document.getElementById('thumbGenPrompt').textContent = promptPack?.gen_prompt || '';

  const preview = document.getElementById('thumbnailPreview');
  const previewWrap = document.getElementById('thumbnailPreviewWrap');
  if (thumbnailUrl) {
    preview.src = thumbnailUrl;
    previewWrap.classList.remove('hidden');
    document.getElementById('thumbnailStudioStatus').textContent = 'Custom thumbnail loaded';
  } else {
    preview.src = '';
    previewWrap.classList.add('hidden');
    document.getElementById('thumbnailStudioStatus').textContent = promptPack?.gen_prompt ? 'Prompt ready' : '';
  }
}

async function copyText(elementId) {
  const text = document.getElementById(elementId)?.textContent || '';
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    document.getElementById('thumbnailStudioStatus').textContent = 'Copied to clipboard';
  } catch (_) {
    document.getElementById('thumbnailStudioStatus').textContent = 'Copy failed';
  }
}

function renderEpisodeLibraryLegacy(episodes) {
  const container = document.getElementById('episodeLibrary');
  if (!episodes || episodes.length === 0) {
    container.innerHTML = '<p class="text-sm text-subtext">No saved podcast episodes yet.</p>';
    return;
  }

  container.innerHTML = '';
  episodes.forEach((episode) => {
    const row = document.createElement('div');
    row.className = 'flex items-center gap-3 rounded-[1.1rem] border border-overlay bg-charcoal p-4';

    const info = document.createElement('div');
    info.className = 'min-w-0 flex-1';

    const title = document.createElement('p');
    title.className = 'text-sm font-semibold text-text truncate';
    title.textContent = episode.title || episode.episode_id;

    const meta = document.createElement('p');
    meta.className = 'text-xs text-subtext mt-1';
    meta.textContent = `${episode.status} โ€ข ${episode.completed_steps}/5 steps โ€ข ${new Date(episode.updated_at).toLocaleString()}`;

    info.appendChild(title);
    info.appendChild(meta);

    const button = document.createElement('button');
    button.className = 'glass-btn glass-btn-primary glass-btn-sm shrink-0 px-3 py-2 rounded-lg text-xs font-bold';
    button.textContent = 'Open';
    button.onclick = () => loadEpisode(episode.episode_id);

    row.appendChild(info);
    row.appendChild(button);
    container.appendChild(row);
  });
}

function renderEpisodeLibrary(episodes) {
  const container = document.getElementById('episodeLibrary');
  if (!episodes || episodes.length === 0) {
    container.innerHTML = '<p class="text-sm text-subtext">No saved podcast episodes yet.</p>';
    return;
  }

  container.innerHTML = '';
  episodes.forEach((episode) => {
    const row = document.createElement('div');
    row.className = 'flex items-center gap-3 rounded-[1.1rem] border border-overlay bg-charcoal p-4';

    const info = document.createElement('div');
    info.className = 'min-w-0 flex-1';

    const titleRow = document.createElement('div');
    titleRow.className = 'flex items-center gap-2 min-w-0';

    const title = document.createElement('p');
    title.className = 'text-sm font-semibold text-text truncate';
    title.textContent = episode.title || episode.episode_id;
    titleRow.appendChild(title);

    if (episode.is_uploaded) {
      const uploadedBadge = document.createElement('span');
      uploadedBadge.className = 'state-pill is-auto shrink-0 text-[10px] uppercase tracking-wide font-bold';
      uploadedBadge.textContent = 'Uploaded';
      titleRow.appendChild(uploadedBadge);
    }

    const meta = document.createElement('p');
    meta.className = 'text-xs text-subtext mt-1';
    const uploadedLabel = episode.is_uploaded ? ' โ€ข history' : '';
    meta.textContent = `${episode.status} โ€ข ${episode.completed_steps}/5 steps${uploadedLabel} โ€ข ${new Date(episode.updated_at).toLocaleString()}`;

    info.appendChild(titleRow);
    info.appendChild(meta);

    const button = document.createElement('button');
    button.className = 'glass-btn glass-btn-primary glass-btn-sm shrink-0 px-3 py-2 rounded-lg text-xs font-bold';
    button.textContent = 'Open';
    button.onclick = () => loadEpisode(episode.episode_id);

    row.appendChild(info);
    row.appendChild(button);
    container.appendChild(row);
  });
}

function showEpisodeDir(dir) {
  const info = document.getElementById('episodeDirInfo');
  const path = document.getElementById('episodeDirPath');
  info.classList.remove('hidden');
  path.textContent = dir;
}

function showManualUploadRow(episodeDir) {
  const row = document.getElementById('manualUploadRow');
  row.classList.remove('hidden');
  row.classList.add('flex');
  const videoPath = episodeDir ? episodeDir.replace(/\\/g, '/') + '/final.mp4' : 'final.mp4';
  document.getElementById('videoFilePath').textContent = videoPath;
}

function copyVideoPath(btn) {
  const pathEl = document.getElementById('videoFilePath');
  navigator.clipboard.writeText(pathEl.textContent).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy Path'; }, 2000);
  });
}

