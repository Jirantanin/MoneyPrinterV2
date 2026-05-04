async function shorts_loadAccounts() {
  try {
    var res = await fetch('/shorts/api/accounts');
    var data = await res.json();
    var accounts = data.accounts || [];
    shorts_youtubeAuth = data.youtube_auth || { authenticated: false, message: '' };
    var select = document.getElementById('shorts-accountSelect');
    var warning = document.getElementById('shorts-noAccountsWarning');

    if (accounts.length === 0) {
      select.classList.add('hidden');
      warning.classList.remove('hidden');
      return;
    }

    warning.classList.add('hidden');
    select.classList.remove('hidden');
    select.innerHTML = '';
    accounts.forEach(function(acc) {
      var opt = document.createElement('option');
      opt.value = acc.id;
      opt.textContent = acc.nickname + ' (' + (acc.niche || 'no niche') + ')';
      opt.dataset.niche = acc.niche || '';
      opt.dataset.language = acc.language || 'English';
      select.appendChild(opt);
    });

    shorts_onAccountChange();
    shorts_applyYoutubeAuthStatus();
  } catch (err) {
    shorts_youtubeAuth = { authenticated: false, message: 'Failed to check YouTube auth status.' };
    document.getElementById('shorts-accountSelect').innerHTML = '<option value="">Failed to load accounts</option>';
    shorts_applyYoutubeAuthStatus();
  }
}

async function shorts_startGenerate() {
  var accountId = document.getElementById('shorts-accountSelect').value;
  if (!accountId) {
    shorts_showError('Select a YouTube account first.');
    return;
  }
  if (shorts_isGenerating) return;

  var topic = document.getElementById('shorts-topicInput').value.trim();
  var niche = document.getElementById('shorts-nicheInput').value.trim();
  var language = document.getElementById('shorts-languageInput').value.trim() || 'English';
  var mode = document.getElementById('shorts-modeToggle').checked ? 'step' : 'auto';

  shorts_isGenerating = true;
  shorts_resetUI();
  document.getElementById('shorts-generateBtn').disabled = true;
  document.getElementById('shorts-cancelBtn').classList.remove('hidden');
  shorts_lockModeToggle(true);

  var res;
  try {
    res = await fetch('/shorts/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: accountId, topic: topic, niche: niche, language: language, mode: mode }),
    });
  } catch (err) {
    shorts_showError('Failed to connect to server: ' + err.message);
    shorts_onGenerationEnd();
    return;
  }

  var data = await res.json();
  if (data.error) {
    shorts_showError(data.error);
    shorts_onGenerationEnd();
    return;
  }
  shorts_currentShortId = data.short_id;
  shorts_appendLog('Started short: ' + shorts_currentShortId);

  shorts_connectSSE(shorts_currentShortId);
  shorts_startImagePolling();
}

function shorts_connectSSE(id) {
  if (shorts_eventSource) { shorts_eventSource.close(); shorts_eventSource = null; }
  shorts_eventSource = new EventSource('/shorts/api/stream/' + id);
  shorts_eventSource.onmessage = function(e) {
    var evt;
    try { evt = JSON.parse(e.data); } catch(ex) { return; }
    shorts_handleSSEEvent(evt);
    if (evt.type === 'complete' || evt.type === 'error' || evt.type === 'cancelled') {
      shorts_eventSource.close();
      shorts_eventSource = null;
      shorts_stopImagePolling();
      shorts_onGenerationEnd();
      if (evt.type === 'complete') {
        shorts_fetchShortData();
      } else if (evt.type === 'cancelled') {
        shorts_appendLog('Generation cancelled.');
      } else {
        shorts_showError(evt.message || 'Pipeline error. Check server logs.');
      }
    }
  };
  shorts_eventSource.onerror = function() {};
}

async function shorts_cancelPipeline() {
  if (!shorts_currentShortId) return;
  try {
    await fetch('/shorts/api/cancel/' + shorts_currentShortId, { method: 'POST' });
  } catch (_) {}
}

// Approve step
async function shorts_approveStep() {
  if (!shorts_currentShortId) return;
  document.getElementById('shorts-approveBanner').classList.add('hidden');
  document.getElementById('shorts-approveBtn').disabled = true;
  try {
    await fetch('/shorts/api/approve/' + shorts_currentShortId, { method: 'POST' });
  } catch (_) {}
  document.getElementById('shorts-approveBtn').disabled = false;
}

// SSE event handler
function shorts_handleSSEEvent(evt) {
  if (evt.type === 'step_start') {
    var i = evt.step;
    if (i >= 0 && i < shorts_stepStates.length) {
      shorts_stepStates[i].status = 'running';
      shorts_stepStates[i].message = '';
      shorts_updateStepUI(i);
    }
  } else if (evt.type === 'step_done') {
    var i = evt.step;
    if (i >= 0 && i < shorts_stepStates.length) {
      shorts_stepStates[i].status = 'done';
      shorts_updateStepUI(i);
      if (i === 3 || i === 8) shorts_fetchShortData();
    }
  } else if (evt.type === 'step_error') {
    var i = evt.step;
    if (i >= 0 && i < shorts_stepStates.length) {
      shorts_stepStates[i].status = 'error';
      shorts_stepStates[i].message = evt.error || 'Error';
      shorts_updateStepUI(i);
    }
    shorts_appendLog('ERROR step ' + evt.step + ': ' + (evt.error || ''), true);
  } else if (evt.type === 'log') {
    var i = typeof evt.step === 'number' ? evt.step : -1;
    if (i >= 0 && i < shorts_stepStates.length && shorts_stepStates[i].status === 'running') {
      shorts_stepStates[i].message = evt.message || '';
      shorts_updateStepUI(i);
    }
    shorts_appendLog(evt.message || '');
  } else if (evt.type === 'waiting_approval') {
    var nextName = evt.next_name || SHORTS_STEP_NAMES[evt.next_step] || 'next step';
    document.getElementById('shorts-approveNextLabel').textContent = 'Next: ' + nextName;
    document.getElementById('shorts-approveBanner').classList.remove('hidden');
  }
}

// Log
async function shorts_fetchImages() {
  if (!shorts_currentShortId) return;
  try {
    var ep = await shorts_fetchShortState();
    if (!ep || !ep.run_dir) return;
  } catch (_) {}
}

async function shorts_fetchShortState() {
  if (!shorts_currentShortId) return null;
  try {
    var res = await fetch('/shorts/api/episode/' + shorts_currentShortId);
    if (!res.ok) return null;
    return await res.json();
  } catch (_) { return null; }
}

async function shorts_fetchShortData() {
  var data = await shorts_fetchShortState();
  if (!data) return;
  shorts_currentEpisodeData = data || {};

  if (data.metadata && Object.keys(data.metadata).length > 0) {
    shorts_renderMetadata(data.metadata);
  }

  shorts_renderReviewPack(data);

  if (data.video_url) {
    shorts_renderVideoPreview(data.video_url);
  }

  if (data.run_dir) {
    document.getElementById('shorts-runDirInfo').classList.remove('hidden');
    document.getElementById('shorts-runDirPath').textContent = data.run_dir;
  }

  if (data.status === 'done' && shorts_youtubeAuth && shorts_youtubeAuth.authenticated) {
    document.getElementById('shorts-uploadBtn').disabled = false;
  }
  shorts_applyYoutubeAuthStatus();
}

async function shorts_uploadVideo() {
  if (!shorts_currentShortId) return;
  if (!(shorts_youtubeAuth && shorts_youtubeAuth.authenticated)) {
    shorts_applyYoutubeAuthStatus();
    return;
  }
  document.getElementById('shorts-uploadBtn').disabled = true;
  var statusEl = document.getElementById('shorts-uploadStatus');
  statusEl.className = 'text-sm text-subtext';
  statusEl.textContent = 'Uploading...';

  try {
    var res = await fetch('/shorts/api/upload/' + shorts_currentShortId, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    var data = await res.json();
    if (data.video_url) {
      statusEl.innerHTML = 'Uploaded: <a href="' + data.video_url + '" target="_blank" class="text-sky underline">' + data.video_url + '</a>';
      statusEl.className = 'text-sm text-accent';
    } else {
      if (data.manual_upload_recommended) {
        statusEl.className = 'text-sm text-yellow-100';
        statusEl.textContent = (data.error || 'YouTube auth unavailable') + ' Use the run folder below to upload manually.';
      } else {
        shorts_showError(data.error || 'Upload failed');
        document.getElementById('shorts-uploadBtn').disabled = false;
      }
    }
  } catch (err) {
    shorts_showError('Upload request failed: ' + err.message);
    document.getElementById('shorts-uploadBtn').disabled = false;
  }
}

// Recent Shorts
async function shorts_loadRecentShorts() {
  var container = document.getElementById('shorts-recentShortsList');
  try {
    var res = await fetch('/shorts/api/shorts');
    var data = await res.json();
    var shorts_list = data.shorts || [];

    if (shorts_list.length === 0) {
      container.innerHTML = '<p class="text-sm text-subtext">No shorts yet.</p>';
      return;
    }

    container.innerHTML = '';
    shorts_list.forEach(function(s) {
      var row = document.createElement('div');
      row.className = 'flex items-center gap-3 rounded-[1.1rem] border border-overlay bg-charcoal p-4';

      var info = document.createElement('div');
      info.className = 'min-w-0 flex-1';

      var title = document.createElement('p');
      title.className = 'text-sm font-semibold text-text truncate';
      title.textContent = s.title || s.dir_name;

      var meta = document.createElement('p');
      meta.className = 'text-xs text-subtext mt-1';
      meta.textContent = s.status + ' โ€ข ' + (s.has_video ? 'video ready' : 'no video') + ' โ€ข ' + new Date(s.updated_at).toLocaleString();

      info.appendChild(title);
      info.appendChild(meta);

      var btn = document.createElement('button');
      btn.className = 'glass-btn glass-btn-primary glass-btn-sm shrink-0 px-3 py-2 rounded-lg text-xs font-bold';
      btn.textContent = 'Open';
      btn.onclick = function() { shorts_loadShort(s.short_id, s.video_filename); };

      row.appendChild(info);
      row.appendChild(btn);
      container.appendChild(row);
    });

    if (!shorts_currentShortId && !shorts_isGenerating && !shorts_hasAutoLoaded && shorts_list.length > 0) {
      var best = shorts_list.find(function(s) { return s.has_video; }) || shorts_list[0];
      if (best) {
        shorts_hasAutoLoaded = true;
        shorts_loadShort(best.short_id, best.video_filename);
      }
    }
  } catch (err) {
    container.innerHTML = '<p class="text-sm text-rose">Failed to load recent shorts.</p>';
  }
}

function shorts_loadShort(id, videoFilename) {
  shorts_currentShortId = id;
  shorts_resetUI();
  shorts_appendLog('Loaded: ' + id);
  shorts_fetchShortData();
  if (videoFilename) {
    shorts_renderVideoPreview('/shorts/static/' + id + '/' + videoFilename);
    if (shorts_youtubeAuth && shorts_youtubeAuth.authenticated) {
      document.getElementById('shorts-uploadBtn').disabled = false;
    }
  }
  shorts_applyYoutubeAuthStatus();
}

// Helpers
