function shorts_applyYoutubeAuthStatus() {
  var uploadBtn = document.getElementById('shorts-uploadBtn');
  var statusEl = document.getElementById('shorts-uploadStatus');
  if (!uploadBtn || !statusEl) return;

  var readyForUpload = !!(shorts_currentEpisodeData && shorts_currentEpisodeData.ready_for_upload);
  if (shorts_youtubeAuth && shorts_youtubeAuth.authenticated) {
    if (!shorts_isGenerating && readyForUpload) {
      uploadBtn.disabled = false;
    }
    if (!statusEl.textContent || statusEl.textContent.indexOf('Uploading') === 0 || statusEl.textContent.indexOf('Copied') === 0) {
      statusEl.className = 'text-sm text-subtext';
      statusEl.textContent = 'YouTube upload is available.';
    }
    return;
  }

  uploadBtn.disabled = true;
  statusEl.className = 'text-sm text-yellow-100';
  statusEl.textContent = (shorts_youtubeAuth && shorts_youtubeAuth.message)
    ? shorts_youtubeAuth.message + ' Use the run folder below to upload manually.'
    : 'YouTube auth unavailable. Use the run folder below to upload manually.';
}

function shorts_renderStepsPanel() {
  var panel = document.getElementById('shorts-stepsPanel');
  panel.innerHTML = '';
  shorts_stepStates.forEach(function(step, i) {
    var row = document.createElement('div');
    row.id = 'shorts-step-row-' + i;
    row.className = 'state-row ' +
      (step.status === 'running' ? 'is-running' : step.status === 'done' ? 'is-done' : step.status === 'error' ? 'is-error' : '');

    var iconWrap = document.createElement('div');
    iconWrap.id = 'shorts-step-icon-' + i;
    iconWrap.className = 'state-icon';
    iconWrap.innerHTML = shorts_iconForStatus(step.status);

    var textBlock = document.createElement('div');
    textBlock.className = 'flex-1 min-w-0';

    var nameEl = document.createElement('div');
    nameEl.className = shorts_colorForStatus(step.status);
    nameEl.textContent = (i + 1) + '. ' + step.name;

    var msgEl = document.createElement('div');
    msgEl.id = 'shorts-step-msg-' + i;
    msgEl.className = 'state-message truncate';
    msgEl.textContent = step.message || '';

    textBlock.appendChild(nameEl);
    textBlock.appendChild(msgEl);
    row.appendChild(iconWrap);
    row.appendChild(textBlock);
    panel.appendChild(row);
  });
}

function shorts_iconForStatus(status) {
  switch (status) {
    case 'pending': return '<span class="text-overlay text-base leading-none">&#9711;</span>';
    case 'running': return '<div class="step-spinner"></div>';
    case 'done':    return '<span class="text-accent text-base leading-none font-bold">&#10003;</span>';
    case 'error':   return '<span class="text-rose text-base leading-none font-bold">&#10007;</span>';
    default:        return '';
  }
}

function shorts_colorForStatus(status) {
  switch (status) {
    case 'running': return 'state-name state-running';
    case 'done':    return 'state-name state-done';
    case 'error':   return 'state-name state-error';
    default:        return 'state-name state-pending';
  }
}

function shorts_updateStepUI(index) {
  var step = shorts_stepStates[index];
  var row = document.getElementById('shorts-step-row-' + index);
  var icon = document.getElementById('shorts-step-icon-' + index);
  var msg = document.getElementById('shorts-step-msg-' + index);
  if (!row || !icon || !msg) return;

  row.className = 'state-row ' +
    (step.status === 'running' ? 'is-running' : step.status === 'done' ? 'is-done' : step.status === 'error' ? 'is-error' : '');
  icon.innerHTML = shorts_iconForStatus(step.status);

  var nameEl = row.querySelector('div.flex-1 > div:first-child');
  if (nameEl) nameEl.className = shorts_colorForStatus(step.status);
  msg.textContent = step.message || '';
}

// Reset UI
function shorts_clearLog() {
  document.getElementById('shorts-logOutput').innerHTML = '';
}

// Generate
function shorts_appendLog(msg, isError) {
  var log = document.getElementById('shorts-logOutput');
  var placeholder = log.querySelector('.text-overlay');
  if (placeholder) placeholder.remove();

  var line = document.createElement('div');
  line.className = isError ? 'text-rose' : 'text-subtext';
  line.textContent = msg;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// Image polling
function shorts_addImageToGallery(filename) {
  if (shorts_renderedImages.has(filename)) return;
  shorts_renderedImages.add(filename);

  var gallery = document.getElementById('shorts-imageGallery');
  var placeholder = document.getElementById('shorts-noImagesMsg');
  if (placeholder) placeholder.remove();

  var a = document.createElement('a');
  a.href = '/shorts/static/' + shorts_currentShortId + '/' + filename;
  a.target = '_blank';
  a.title = filename;
    a.className = 'image-card block aspect-video rounded-2xl overflow-hidden bg-charcoal fade-in';

  var img = document.createElement('img');
  img.src = '/shorts/static/' + shorts_currentShortId + '/' + filename;
  img.alt = filename;
  img.className = 'w-full h-full object-cover';
  img.loading = 'lazy';
  img.onerror = function() { a.remove(); shorts_renderedImages.delete(filename); };

  a.appendChild(img);
  gallery.appendChild(a);
}

// Short data fetch
function shorts_renderVideoPreview(videoUrl) {
  var player = document.getElementById('shorts-videoPreviewPlayer');
  var skeleton = document.getElementById('shorts-videoPreviewSkeleton');
  var status = document.getElementById('shorts-videoPreviewStatus');

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

function shorts_renderMetadata(metadata) {
  var panel = document.getElementById('shorts-metadataPanel');
  var content = document.getElementById('shorts-metadataContent');
  var review = shorts_currentEpisodeData.review || {};
  var readyForUpload = !!(shorts_currentEpisodeData.ready_for_upload || review.ready_for_upload);
  panel.classList.remove('hidden');
  content.innerHTML = '';

  var header = document.createElement('div');
  header.className = 'rounded-[1rem] border border-overlay bg-charcoal p-4 space-y-3';

  var headerRow = document.createElement('div');
  headerRow.className = 'flex flex-wrap items-start justify-between gap-3';

  var headerText = document.createElement('div');
  var headerTitle = document.createElement('p');
  headerTitle.className = 'text-xs font-semibold uppercase tracking-[0.18em] text-subtext';
  headerTitle.textContent = 'Metadata';
  headerText.appendChild(headerTitle);

  var headerDesc = document.createElement('p');
  headerDesc.className = 'text-xs text-subtext mt-1';
  headerDesc.textContent = 'Copy-ready title, description, and tags before upload.';
  headerText.appendChild(headerDesc);

  var statusBadge = document.createElement('span');
  statusBadge.className = readyForUpload
    ? 'inline-flex items-center rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-emerald-200'
    : 'inline-flex items-center rounded-full border border-yellow-400/30 bg-yellow-500/10 px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-yellow-100';
  statusBadge.textContent = readyForUpload ? 'Ready for Upload' : 'Needs Review';

  var actionRow = document.createElement('div');
  actionRow.className = 'flex flex-wrap gap-2';
  actionRow.appendChild(shorts_makeCopyButton('Title', function() { return (shorts_currentEpisodeData.metadata && shorts_currentEpisodeData.metadata.title) || metadata.title || ''; }));
  actionRow.appendChild(shorts_makeCopyButton('Description', function() { return (shorts_currentEpisodeData.metadata && shorts_currentEpisodeData.metadata.description) || metadata.description || ''; }));
  actionRow.appendChild(shorts_makeCopyButton('Tags', function() {
    var tags = (shorts_currentEpisodeData.metadata && shorts_currentEpisodeData.metadata.tags) || metadata.tags || [];
    return Array.isArray(tags) ? tags.join(', ') : String(tags || '');
  }));
  actionRow.appendChild(shorts_makeCopyButton('All', function() {
    var tags = (shorts_currentEpisodeData.metadata && shorts_currentEpisodeData.metadata.tags) || metadata.tags || [];
    var pieces = [];
    if (metadata.title) pieces.push('Title: ' + metadata.title);
    if (metadata.description) pieces.push('Description:\n' + metadata.description);
    if (Array.isArray(tags) && tags.length) pieces.push('Tags: ' + tags.join(', '));
    return pieces.join('\n\n');
  }));

  var headerActions = document.createElement('div');
  headerActions.className = 'flex flex-wrap items-center justify-end gap-2';
  headerActions.appendChild(statusBadge);
  headerActions.appendChild(actionRow);

  headerRow.appendChild(headerText);
  headerRow.appendChild(headerActions);
  header.appendChild(headerRow);
  content.appendChild(header);

  if (metadata.title) {
    var titleBlock = document.createElement('div');
    titleBlock.className = 'rounded-[1rem] border border-overlay bg-[rgba(255,255,255,0.02)] p-4';

    var titleLabel = document.createElement('p');
    titleLabel.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-subtext mb-1';
    titleLabel.textContent = 'Title';

    var titleEl = document.createElement('p');
    titleEl.className = 'text-[1rem] font-semibold text-text leading-snug tracking-[-0.025em]';
    titleEl.textContent = metadata.title;

    titleBlock.appendChild(titleLabel);
    titleBlock.appendChild(titleEl);
    content.appendChild(titleBlock);
  }

  if (metadata.description) {
    var descBlock = document.createElement('div');
    descBlock.className = 'rounded-[1rem] border border-overlay bg-[rgba(255,255,255,0.02)] p-4';

    var descLabel = document.createElement('p');
    descLabel.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-subtext mb-1';
    descLabel.textContent = 'Description';

    var descEl = document.createElement('p');
    descEl.className = 'text-xs text-subtext whitespace-pre-wrap leading-relaxed max-h-32 overflow-y-auto';
    descEl.textContent = metadata.description;

    descBlock.appendChild(descLabel);
    descBlock.appendChild(descEl);
    content.appendChild(descBlock);
  }

  if (metadata.tags && metadata.tags.length > 0) {
    var tagsBlock = document.createElement('div');
    tagsBlock.className = 'rounded-[1rem] border border-overlay bg-[rgba(255,255,255,0.02)] p-4';

    var tagsLabel = document.createElement('p');
    tagsLabel.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-subtext mb-2';
    tagsLabel.textContent = 'Tags';

    var tagsWrap = document.createElement('div');
    tagsWrap.className = 'flex flex-wrap gap-2';
    metadata.tags.forEach(function(tag) {
      var chip = document.createElement('span');
      chip.className = 'inline-flex items-center rounded-full border border-overlay bg-charcoal px-3 py-1 text-xs text-text';
      chip.textContent = tag;
      tagsWrap.appendChild(chip);
    });

    tagsBlock.appendChild(tagsLabel);
    tagsBlock.appendChild(tagsWrap);
    content.appendChild(tagsBlock);
  }
}

function shorts_makeCopyButton(label, getText) {
  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'glass-link text-xs text-sky hover:underline';
  btn.textContent = 'Copy ' + label;
  btn.onclick = function() {
    var text = '';
    try {
      text = String(getText ? getText() : '').trim();
    } catch (_) {
      text = '';
    }
    if (!text) return;
    shorts_copyToClipboard(text);
  };
  return btn;
}

async function shorts_copyToClipboard(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', 'true');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    document.getElementById('shorts-uploadStatus').textContent = 'Copied to clipboard';
  } catch (err) {
    shorts_showError('Copy failed: ' + err.message);
  }
}

function shorts_renderReviewPack(data) {
  var panel = document.getElementById('shorts-reviewPanel');
  var content = document.getElementById('shorts-reviewContent');
  var review = (data && data.review) || {};
  var discovery = (data && data.discovery) || {};
  var discoveryWinner = discovery.winner || {};
  var discoveryTopic = String(review.discovery_topic || discoveryWinner.topic || '').trim();
  var discoveryAngle = String(review.discovery_angle || discoveryWinner.angle || '').trim();
  var readyForUpload = !!((data && data.ready_for_upload) || review.ready_for_upload);
  var qualityNotes = Array.isArray((data && data.quality_notes)) ? data.quality_notes : (Array.isArray(review.quality_notes) ? review.quality_notes : []);
  content.innerHTML = '';

  var scriptText = '';
  var hookText = '';
  var imagePrompts = [];
  var scenes = [];

  if (data) {
    if (data.script) scriptText = String(data.script).trim();
    else if (data.script_text) scriptText = String(data.script_text).trim();
    else if (data.full_script) scriptText = String(data.full_script).trim();

    if (data.hook) hookText = String(data.hook).trim();
    else if (data.opening_hook) hookText = String(data.opening_hook).trim();
    else if (data.hook_text) hookText = String(data.hook_text).trim();

    if (Array.isArray(data.image_prompts)) imagePrompts = data.image_prompts.slice();
    if (Array.isArray(data.scenes)) scenes = data.scenes.slice();
  }

  if (!scriptText && scenes.length > 0) {
    scriptText = scenes.map(function(scene) {
      return scene && scene.narration ? String(scene.narration).trim() : '';
    }).filter(Boolean).join('\n\n');
  }

  if (!imagePrompts.length && scenes.length > 0) {
    imagePrompts = scenes.map(function(scene) {
      return scene && scene.image_prompt ? String(scene.image_prompt).trim() : '';
    }).filter(Boolean);
  }

  if (!hookText && scriptText) {
    hookText = scriptText.split(/\n+/)[0] || '';
  }

  if (!scriptText && !hookText && !imagePrompts.length) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');

  var header = document.createElement('div');
  header.className = 'rounded-[1rem] border border-overlay bg-charcoal p-4 flex flex-wrap items-start justify-between gap-3';

  var headingWrap = document.createElement('div');
  var heading = document.createElement('p');
  heading.className = 'text-xs font-semibold uppercase tracking-[0.18em] text-subtext';
  heading.textContent = 'Review Pack';
  headingWrap.appendChild(heading);

  var desc = document.createElement('p');
  desc.className = 'text-xs text-subtext mt-1';
  desc.textContent = 'Script, hook, and image prompts if the API sends them.';
  headingWrap.appendChild(desc);

  var statusBadge = document.createElement('span');
  statusBadge.className = readyForUpload
    ? 'inline-flex items-center rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-emerald-200'
    : 'inline-flex items-center rounded-full border border-yellow-400/30 bg-yellow-500/10 px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-yellow-100';
  statusBadge.textContent = readyForUpload ? 'Ready for Upload' : 'Needs Review';

  var copyAll = document.createElement('button');
  copyAll.type = 'button';
  copyAll.className = 'glass-link text-xs text-sky hover:underline';
  copyAll.textContent = 'Copy All Review Text';
  copyAll.onclick = function() {
    var pieces = [];
    if (hookText) pieces.push('Hook:\n' + hookText);
    if (scriptText) pieces.push('Script:\n' + scriptText);
    if (imagePrompts.length) {
      pieces.push('Image Prompts:\n' + imagePrompts.map(function(prompt, idx) {
        return (idx + 1) + '. ' + prompt;
      }).join('\n'));
    }
    shorts_copyToClipboard(pieces.join('\n\n'));
  };

  var headerActions = document.createElement('div');
  headerActions.className = 'flex flex-wrap items-center justify-end gap-2';
  headerActions.appendChild(statusBadge);
  headerActions.appendChild(copyAll);

  header.appendChild(headingWrap);
  header.appendChild(headerActions);
  content.appendChild(header);

  if (discoveryTopic || discoveryAngle) {
    var discoveryWrap = document.createElement('div');
    discoveryWrap.className = 'rounded-[1rem] border border-overlay bg-[rgba(255,255,255,0.02)] p-4 space-y-3';

    var discoveryTop = document.createElement('div');
    discoveryTop.className = 'flex items-center justify-between gap-3';

    var discoveryLabel = document.createElement('p');
    discoveryLabel.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-subtext';
    discoveryLabel.textContent = 'Discovery Result';

    var copyDiscovery = document.createElement('button');
    copyDiscovery.type = 'button';
    copyDiscovery.className = 'glass-link text-xs text-sky hover:underline';
    copyDiscovery.textContent = 'Copy Discovery';
    copyDiscovery.onclick = function() {
      var lines = [];
      if (discoveryTopic) lines.push('Topic: ' + discoveryTopic);
      if (discoveryAngle) lines.push('Angle: ' + discoveryAngle);
      shorts_copyToClipboard(lines.join('\n'));
    };

    discoveryTop.appendChild(discoveryLabel);
    discoveryTop.appendChild(copyDiscovery);
    discoveryWrap.appendChild(discoveryTop);

    if (discoveryTopic) {
      var topicLine = document.createElement('p');
      topicLine.className = 'text-sm font-semibold text-text leading-relaxed';
      topicLine.textContent = discoveryTopic;
      discoveryWrap.appendChild(topicLine);
    }

    if (discoveryAngle) {
      var angleLine = document.createElement('p');
      angleLine.className = 'text-xs text-subtext whitespace-pre-wrap leading-relaxed';
      angleLine.textContent = discoveryAngle;
      discoveryWrap.appendChild(angleLine);
    }

    content.appendChild(discoveryWrap);
  }

  if (qualityNotes.length) {
    var notesWrap = document.createElement('div');
    notesWrap.className = 'rounded-[1rem] border border-yellow-400/20 bg-yellow-500/5 p-4 space-y-2';

    var notesLabel = document.createElement('p');
    notesLabel.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-yellow-100';
    notesLabel.textContent = 'Quality Notes';
    notesWrap.appendChild(notesLabel);

    qualityNotes.forEach(function(note) {
      var item = document.createElement('p');
      item.className = 'text-xs text-yellow-50/90 leading-relaxed';
      item.textContent = 'โ€ข ' + note;
      notesWrap.appendChild(item);
    });

    content.appendChild(notesWrap);
  }

  if (hookText) {
    content.appendChild(shorts_renderReviewCard('Hook', hookText));
  }

  if (scriptText) {
    content.appendChild(shorts_renderReviewCard('Script', scriptText));
  }

  if (imagePrompts.length) {
    content.appendChild(shorts_renderImagePromptCard(imagePrompts));
  }
}

function shorts_renderReviewCard(title, text) {
  var wrap = document.createElement('div');
  wrap.className = 'rounded-[1rem] border border-overlay bg-[rgba(255,255,255,0.02)] p-4 space-y-3';

  var top = document.createElement('div');
  top.className = 'flex items-center justify-between gap-3';

  var label = document.createElement('p');
  label.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-subtext';
  label.textContent = title;

  var copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'glass-link text-xs text-sky hover:underline';
  copy.textContent = 'Copy ' + title;
  copy.onclick = function() { shorts_copyToClipboard(text); };

  top.appendChild(label);
  top.appendChild(copy);

  var body = document.createElement('p');
  body.className = 'text-sm text-text whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto';
  body.textContent = text;

  wrap.appendChild(top);
  wrap.appendChild(body);
  return wrap;
}

function shorts_renderImagePromptCard(prompts) {
  var wrap = document.createElement('div');
  wrap.className = 'rounded-[1rem] border border-overlay bg-[rgba(255,255,255,0.02)] p-4 space-y-3';

  var top = document.createElement('div');
  top.className = 'flex items-center justify-between gap-3';

  var label = document.createElement('p');
  label.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-subtext';
  label.textContent = 'Image Prompts';

  var copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'glass-link text-xs text-sky hover:underline';
  copy.textContent = 'Copy Prompts';
  copy.onclick = function() {
    shorts_copyToClipboard(prompts.map(function(prompt, idx) {
      return (idx + 1) + '. ' + prompt;
    }).join('\n'));
  };

  top.appendChild(label);
  top.appendChild(copy);

  var list = document.createElement('div');
  list.className = 'space-y-2';
  prompts.forEach(function(prompt, idx) {
    var item = document.createElement('div');
    item.className = 'rounded-xl border border-overlay bg-charcoal p-3';

    var num = document.createElement('p');
    num.className = 'text-[0.7rem] uppercase tracking-[0.16em] text-subtext mb-1';
    num.textContent = 'Prompt ' + (idx + 1);

    var text = document.createElement('p');
    text.className = 'text-xs text-text whitespace-pre-wrap leading-relaxed';
    text.textContent = prompt;

    item.appendChild(num);
    item.appendChild(text);
    list.appendChild(item);
  });

  wrap.appendChild(top);
  wrap.appendChild(list);
  return wrap;
}

// Upload
