function renderStepsPanelV2() {
  const panel = document.getElementById('stepsPanelV2');
  panel.innerHTML = '';
  stepStatesV2.forEach((step, i) => {
    const row = document.createElement('div');
    row.id = `step-row-v2-${i}`;
    row.className = 'state-row ' +
      (step.status === 'running' ? 'is-running' : step.status === 'done' ? 'is-done' : step.status === 'error' ? 'is-error' : '');

    const iconWrap = document.createElement('div');
    iconWrap.id = `step-icon-v2-${i}`;
    iconWrap.className = 'state-icon';
    iconWrap.innerHTML = iconForStatusV2(step.status);

    const textBlock = document.createElement('div');
    textBlock.className = 'flex-1 min-w-0';

    const nameEl = document.createElement('div');
    nameEl.className = colorForStatusV2(step.status);
    nameEl.textContent = `${i + 1}. ${step.name}`;

    const msgEl = document.createElement('div');
    msgEl.id = `step-msg-v2-${i}`;
    msgEl.className = 'state-message truncate';
    msgEl.textContent = step.message || '';

    textBlock.appendChild(nameEl);
    textBlock.appendChild(msgEl);

    const actionsWrap = document.createElement('div');
    actionsWrap.id = `step-actions-v2-${i}`;
    actionsWrap.className = 'shrink-0 flex items-center gap-2';
    renderStepActionsV2(actionsWrap, i);

    row.appendChild(iconWrap);
    row.appendChild(textBlock);
    row.appendChild(actionsWrap);
    panel.appendChild(row);
  });
}

function iconForStatusV2(status) {
  switch (status) {
    case 'pending': return '<span class="text-overlay text-base leading-none">&#9711;</span>';
    case 'running': return '<div class="step-spinner"></div>';
    case 'done':    return '<span class="text-accent text-base leading-none font-bold">&#10003;</span>';
    case 'error':   return '<span class="text-rose text-base leading-none font-bold">&#10007;</span>';
    default:        return '';
  }
}

function colorForStatusV2(status) {
  switch (status) {
    case 'running': return 'state-name state-running';
    case 'done':    return 'state-name state-done';
    case 'error':   return 'state-name state-error';
    default:        return 'state-name state-pending';
  }
}

function updateStepUIV2(index) {
  const step = stepStatesV2[index];
  const row = document.getElementById(`step-row-v2-${index}`);
  const icon = document.getElementById(`step-icon-v2-${index}`);
  const msg = document.getElementById(`step-msg-v2-${index}`);
  const actions = document.getElementById(`step-actions-v2-${index}`);

  if (!row || !icon || !msg) return;

  row.className = 'state-row ' +
    (step.status === 'running' ? 'is-running' : step.status === 'done' ? 'is-done' : step.status === 'error' ? 'is-error' : '');

  icon.innerHTML = iconForStatusV2(step.status);

  const nameEl = row.querySelector('div.flex-1 > div:first-child');
  if (nameEl) nameEl.className = colorForStatusV2(step.status);

  msg.textContent = step.message || '';
  if (actions) renderStepActionsV2(actions, index);
}

function canRedoStepV2(stepIndex) {
  if (!episodeIdV2 || isGeneratingV2 || currentEpisodeStatusV2 === 'running' || isCurrentEpisodeUploadedV2) return false;
  if (stepIndex < 0 || stepIndex >= stepStatesV2.length) return false;
  if (currentEpisodeStatusV2 === 'uploaded') return false;
  const nextIncomplete = stepStatesV2.findIndex(step => step.status !== 'done');
  if (nextIncomplete === -1) return true;
  return stepIndex <= nextIncomplete || stepStatesV2[stepIndex].status === 'done' || stepStatesV2[stepIndex].status === 'error';
}

function redoImpactMessageV2(stepIndex) {
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

function renderStepActionsV2(container, stepIndex) {
  container.innerHTML = '';
  if (!canRedoStepV2(stepIndex)) return;

  const redoBtn = document.createElement('button');
  redoBtn.type = 'button';
  redoBtn.className = 'glass-link text-[11px] text-yellow-300 hover:underline';
  redoBtn.textContent = 'Redo from here';
  redoBtn.onclick = () => redoFromStepV2(stepIndex);
  container.appendChild(redoBtn);
}

function renderPodcastLogsV2() {
  const logEl = document.getElementById('podcastV2LogOutput');
  if (!logEl) return;
  if (!podcastLogsV2.length) {
    logEl.textContent = 'Logs will appear here.';
    return;
  }
  logEl.textContent = podcastLogsV2.join('\n');
  logEl.scrollTop = logEl.scrollHeight;
}

function appendPodcastLogV2(message) {
  const text = (message || '').trim();
  if (!text) return;
  podcastLogsV2.push(text);
  if (podcastLogsV2.length > 500) {
    podcastLogsV2 = podcastLogsV2.slice(-500);
  }
  renderPodcastLogsV2();
}

function setPodcastLogsV2(logs) {
  podcastLogsV2 = Array.isArray(logs) ? logs.slice(-500) : [];
  renderPodcastLogsV2();
}

function clearPodcastLogsV2() {
  podcastLogsV2 = [];
  renderPodcastLogsV2();
}

function formatCostUsdV2(value) {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount)) return '$0.0000';
  if (amount > 0 && amount < 0.01) return `$${amount.toFixed(6)}`;
  return `$${amount.toFixed(4)}`;
}

function providerLabelV2(provider) {
  const labels = {
    anthropic: 'Claude script',
    gemini_image: 'Gemini image',
    runware_flux1_image: 'FLUX.1 image',
    kling_image2video: 'Kling video',
    pexels_video: 'Pexels',
    pixabay_video: 'Pixabay',
    edge_tts: 'Edge TTS',
    elevenlabs_tts: 'ElevenLabs TTS',
    gemini_tts: 'Gemini TTS',
  };
  return labels[provider] || provider;
}

function providerUsageTextV2(provider, item, summary) {
  const usage = item?.usage || {};
  if (provider === 'anthropic') {
    const input = Number(usage.input_tokens || 0);
    const output = Number(usage.output_tokens || 0);
    const calls = Number(summary?.calls || 0);
    return `${calls} calls / ${(input + output).toLocaleString()} tokens`;
  }
  if (usage.usd) return 'actual API cost';
  const parts = [];
  if (usage.requests) parts.push(`${Math.round(Number(usage.requests)).toLocaleString()} requests`);
  if (usage.chars) parts.push(`${Math.round(Number(usage.chars)).toLocaleString()} chars`);
  if (usage.seconds) parts.push(`${Math.round(Number(usage.seconds)).toLocaleString()} sec`);
  if (parts.length) return parts.join(' / ');
  return 'tracked';
}

function clearCostEstimateV2() {
  const panel = document.getElementById('costEstimatePanelV2');
  if (!panel) return;
  panel.classList.remove('hidden');
  document.getElementById('costEstimateTotalV2').textContent = '$0.0000';
  document.getElementById('costEstimateStatusV2').textContent = 'waiting';
  document.getElementById('costEstimateBreakdownV2').innerHTML =
    '<p class="text-subtext sm:col-span-2">Cost will appear after generation finishes.</p>';
}

function renderCostEstimateV2(summary) {
  const panel = document.getElementById('costEstimatePanelV2');
  if (!panel) return;
  if (!summary || !summary.run_id) {
    clearCostEstimateV2();
    return;
  }

  panel.classList.remove('hidden');
  const total = Number(summary.cost_usd || 0);
  document.getElementById('costEstimateTotalV2').textContent = formatCostUsdV2(total);
  document.getElementById('costEstimateStatusV2').textContent =
    summary.status === 'done' ? 'final' : summary.status || 'tracked';

  const breakdown = summary.provider_breakdown || {};
  const items = Object.entries(breakdown)
    .filter(([, item]) => {
      const cost = Number(item?.estimated_cost_usd || 0);
      const usage = item?.usage || {};
      return cost > 0 || Object.values(usage).some(value => Number(value || 0) > 0);
    })
    .sort((a, b) => Number(b[1]?.estimated_cost_usd || 0) - Number(a[1]?.estimated_cost_usd || 0));

  const container = document.getElementById('costEstimateBreakdownV2');
  container.innerHTML = '';
  if (!items.length) {
    const empty = document.createElement('p');
    empty.className = 'text-subtext sm:col-span-2';
    empty.textContent = 'No paid usage tracked yet.';
    container.appendChild(empty);
    return;
  }

  items.forEach(([provider, item]) => {
    const row = document.createElement('div');
    row.className = 'rounded-lg border border-overlay/70 bg-surface/60 px-3 py-2 min-w-0';

    const top = document.createElement('div');
    top.className = 'flex items-center justify-between gap-3';

    const name = document.createElement('span');
    name.className = 'font-medium text-text truncate';
    name.textContent = providerLabelV2(provider);

    const cost = document.createElement('span');
    cost.className = 'font-semibold text-accent shrink-0';
    cost.textContent = formatCostUsdV2(item?.estimated_cost_usd || 0);

    const usage = document.createElement('div');
    usage.className = 'mt-1 text-[11px] text-subtext truncate';
    usage.textContent = providerUsageTextV2(provider, item, summary);

    top.appendChild(name);
    top.appendChild(cost);
    row.appendChild(top);
    row.appendChild(usage);
    container.appendChild(row);
  });
}

function clearMetadataViewV2() {
  document.getElementById('metadataPanelV2').classList.add('hidden');
  document.getElementById('metadataActionsV2').classList.add('hidden');
  document.getElementById('metadataContentV2').innerHTML = '';
  currentMetadataV2 = {};
}

function clearThumbnailStudioV2() {
  document.getElementById('thumbnailStudioV2').classList.add('hidden');
  document.getElementById('thumbHeadlineV2').textContent = '';
  document.getElementById('thumbSupportV2').textContent = '';
  document.getElementById('thumbPromptV2').textContent = '';
  document.getElementById('thumbGenPromptV2').textContent = '';
  document.getElementById('thumbnailStudioStatusV2').textContent = '';
  document.getElementById('thumbnailUploadStatusV2').textContent = '';
  document.getElementById('thumbnailFileInputV2').value = '';
  document.getElementById('thumbnailPreviewV2').src = '';
  document.getElementById('thumbnailPreviewWrapV2').classList.add('hidden');
  document.getElementById('thumbnailPreviewV2').classList.add('hidden');
  const thumbPlaceholder = document.getElementById('thumbnailPreviewPlaceholderV2');
  if (thumbPlaceholder) thumbPlaceholder.classList.remove('hidden');
}

function hideManualUploadRowV2() {
  const manualRow = document.getElementById('manualUploadRowV2');
  if (manualRow) {
    manualRow.classList.add('hidden');
    manualRow.classList.remove('flex');
  }
}

function prepareRedoUIV2(stepIndex) {
  for (let i = stepIndex; i < stepStatesV2.length; i++) {
    stepStatesV2[i].status = 'pending';
    stepStatesV2[i].message = '';
  }
  renderStepsPanelV2();

  if (stepIndex <= 1) {
    renderedImagesV2 = new Set();
    currentAssetStatusesV2 = [];
    currentSceneCountV2 = stepIndex <= 0 ? 0 : currentSceneCountV2;
    renderImageGalleryV2();
  }
  if (stepIndex <= 0) {
    document.getElementById('scriptPanelV2').innerHTML =
      '<p id="noScriptMsgV2" class="text-subtext text-sm">Script will appear after generation begins.</p>';
  }
  if (stepIndex <= 3) {
    clearMetadataViewV2();
  }
  if (stepIndex <= 4) {
    clearThumbnailStudioV2();
  }
  hideManualUploadRowV2();
  currentEpisodeStatusV2 = 'idle';
  isCurrentEpisodeUploadedV2 = false;
}

function renderVideoPreviewV2(videoUrl) {
  const player = document.getElementById('videoPreviewPlayerV2');
  const skeleton = document.getElementById('videoPreviewSkeletonV2');
  const status = document.getElementById('videoPreviewStatusV2');

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

function canRegenAssetV2(sceneIndex) {
  return !!episodeIdV2 && !isGeneratingV2 && currentEpisodeStatusV2 !== 'running' && !isCurrentEpisodeUploadedV2 && !regeneratingSceneIndicesV2.has(sceneIndex);
}

function renderImageGalleryV2(images) {
  const gallery = document.getElementById('imageGalleryV2');
  const sceneCount = currentSceneCountV2 || currentAssetStatusesV2.length;
  if (!sceneCount) {
    gallery.innerHTML = '<div id="noImagesMsgV2" class="col-span-3 flex items-center justify-center text-subtext text-sm h-32">No images yet</div>';
    return;
  }

  const imageSet = new Set((images || []).filter(name => /^scene_\d+\.png$/.test(name)));
  const statusMap = new Map(
    (currentAssetStatusesV2 || []).map(status => [status.scene_index, status])
  );

  gallery.innerHTML = '';
  for (let i = 0; i < sceneCount; i++) {
    const sceneNum = String(i).padStart(2, '0');
    const filename = `scene_${sceneNum}.png`;
    const status = statusMap.get(i) || {};
    const imageExists = status.image_exists || imageSet.has(filename);
    const audioExists = !!status.audio_exists;
    const imageUrl = status.image_url || (imageExists ? `/static/${episodeIdV2}/${filename}` : '');

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
    regenBtn.textContent = regeneratingSceneIndicesV2.has(i) ? 'Regen...' : 'Regen';
    regenBtn.disabled = !canRegenAssetV2(i);
    regenBtn.onclick = () => regenSceneAssetV2(i);

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

function renderScriptV2(scenes) {
  const panel = document.getElementById('scriptPanelV2');
  const placeholder = document.getElementById('noScriptMsgV2');
  if (placeholder) placeholder.remove();

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

function renderScriptQcV2(report) {
  const panel = document.getElementById('scriptQcPanelV2');
  if (!panel) return;
  const hasReport = report && Object.keys(report).length > 0;
  if (!hasReport) {
    panel.classList.add('hidden');
    panel.textContent = '';
    panel.title = '';
    return;
  }

  const status = String(report.status || 'review').toLowerCase();
  const score = Number.isFinite(Number(report.overall_score))
    ? Math.round(Number(report.overall_score))
    : null;
  const issueCount = Array.isArray(report.issues) ? report.issues.length : 0;

  panel.classList.remove('hidden', 'is-auto', 'is-step');
  panel.classList.add(status === 'pass' ? 'is-auto' : 'is-step');
  panel.textContent = `QC ${status}${score === null ? '' : ` ${score}`}${issueCount ? ` / ${issueCount} issues` : ''}`;
  panel.title = report.summary || 'Script quality report';
}

function renderMetadataV2(metadata) {
  const panel = document.getElementById('metadataPanelV2');
  const actions = document.getElementById('metadataActionsV2');
  const content = document.getElementById('metadataContentV2');
  panel.classList.remove('hidden');
  actions.classList.remove('hidden');
  content.innerHTML = '';
  currentMetadataV2 = metadata || {};

  if (metadata.title) {
    const titleEl = document.createElement('p');
    titleEl.className = 'text-[1.12rem] font-semibold text-text leading-snug tracking-[-0.025em]';
    titleEl.textContent = metadata.title;
    content.appendChild(titleEl);
  }

  if (metadata.description) {
    const descEl = document.createElement('p');
    descEl.className = 'text-sm text-subtext whitespace-pre-wrap leading-relaxed';
    descEl.textContent = metadata.description;
    content.appendChild(descEl);
  }

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

function renderThumbnailStudioV2(promptPack, thumbnailUrl) {
  const panel = document.getElementById('thumbnailStudioV2');
  panel.classList.remove('hidden');

  document.getElementById('thumbHeadlineV2').textContent = promptPack?.headline || '';
  document.getElementById('thumbSupportV2').textContent = promptPack?.supporting_text || '';
  document.getElementById('thumbPromptV2').textContent = promptPack?.canva_prompt || '';
  document.getElementById('thumbGenPromptV2').textContent = promptPack?.gen_prompt || '';

  const preview = document.getElementById('thumbnailPreviewV2');
  const previewWrap = document.getElementById('thumbnailPreviewWrapV2');
  if (thumbnailUrl) {
    preview.src = thumbnailUrl;
    previewWrap.classList.remove('hidden');
    document.getElementById('thumbnailStudioStatusV2').textContent = 'Custom thumbnail loaded';
  } else {
    preview.src = '';
    previewWrap.classList.add('hidden');
    document.getElementById('thumbnailStudioStatusV2').textContent = promptPack?.gen_prompt ? 'Prompt ready' : '';
  }
}

async function copyTextV2(elementId) {
  const text = document.getElementById(elementId)?.textContent || '';
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    document.getElementById('thumbnailStudioStatusV2').textContent = 'Copied to clipboard';
  } catch (_) {
    document.getElementById('thumbnailStudioStatusV2').textContent = 'Copy failed';
  }
}

function renderEpisodeLibraryV2(episodes) {
  const container = document.getElementById('episodeLibraryV2');
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
    const uploadedLabel = episode.is_uploaded ? ' · history' : '';
    meta.textContent = `${episode.status} · ${episode.completed_steps}/5 steps${uploadedLabel} · ${new Date(episode.updated_at).toLocaleString()}`;

    info.appendChild(titleRow);
    info.appendChild(meta);

    const button = document.createElement('button');
    button.className = 'glass-btn glass-btn-primary glass-btn-sm shrink-0 px-3 py-2 rounded-lg text-xs font-bold';
    button.textContent = 'Open';
    button.onclick = () => loadEpisodeV2(episode.episode_id);

    row.appendChild(info);
    row.appendChild(button);
    container.appendChild(row);
  });
}

function showEpisodeDirV2(dir) {
  const info = document.getElementById('episodeDirInfoV2');
  const path = document.getElementById('episodeDirPathV2');
  info.classList.remove('hidden');
  path.textContent = dir;
}

function showManualUploadRowV2(episodeDir) {
  const row = document.getElementById('manualUploadRowV2');
  row.classList.remove('hidden');
  row.classList.add('flex');
  const videoPath = episodeDir ? episodeDir.replace(/\\/g, '/') + '/final.mp4' : 'final.mp4';
  document.getElementById('videoFilePathV2').textContent = videoPath;
}

function copyVideoPathV2(btn) {
  const pathEl = document.getElementById('videoFilePathV2');
  navigator.clipboard.writeText(pathEl.textContent).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy Path'; }, 2000);
  });
}
