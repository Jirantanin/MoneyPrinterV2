// clip_shorts-main.js — Podcast-to-Shorts clip cutter tab logic.
// Loaded by clip_shorts_component.html via /ui-assets/clip_shorts-main.js

// ---------------------------------------------------------------------------
// Episode loader
// ---------------------------------------------------------------------------

function cs_loadEpisodes() {
  var sel = document.getElementById('csEpisodeSelect');
  if (!sel) return;

  sel.innerHTML = '<option value="">Loading…</option>';

  fetch('/podcast/episodes')
    .then(function(r) { return r.json(); })
    .then(function(episodes) {
      if (!episodes || episodes.length === 0) {
        sel.innerHTML = '<option value="">No completed episodes found</option>';
        return;
      }
      sel.innerHTML = '<option value="">— Select an episode —</option>';
      episodes.forEach(function(ep) {
        var opt = document.createElement('option');
        opt.value = ep.episode_dir;
        var label = ep.topic
          ? ep.topic + ' (' + ep.scene_count + ' scenes)'
          : ep.episode_dir + ' (' + ep.scene_count + ' scenes)';
        opt.textContent = label;
        sel.appendChild(opt);
      });
    })
    .catch(function(err) {
      sel.innerHTML = '<option value="">Error loading episodes</option>';
      console.error('cs_loadEpisodes error:', err);
    });
}

// ---------------------------------------------------------------------------
// Generation (SSE stream)
// ---------------------------------------------------------------------------

function cs_generate() {
  var episodeDir = (document.getElementById('csEpisodeSelect') || {}).value || '';
  var topN = parseInt((document.getElementById('csTopN') || {}).value, 10) || 3;

  if (!episodeDir) {
    alert('Please select an episode first.');
    return;
  }
  topN = Math.max(1, Math.min(5, topN));

  // Reset UI
  document.getElementById('csProgressWrap').classList.remove('hidden');
  document.getElementById('csResults').innerHTML = '';
  document.getElementById('csLog').textContent = '';
  cs_setGenerating(true);

  fetch('/podcast/clip-shorts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ episode_dir: episodeDir, top_n: topN }),
  }).then(function(res) {
    if (!res.ok) {
      return res.json().then(function(body) {
        cs_appendLog('ERROR: ' + (body.error || res.statusText));
        cs_setGenerating(false);
      });
    }

    var reader = res.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';

    function pump() {
      reader.read().then(function(chunk) {
        if (chunk.done) {
          cs_setGenerating(false);
          return;
        }

        buf += decoder.decode(chunk.value, { stream: true });
        var lines = buf.split('\n');
        buf = lines.pop(); // keep incomplete last line

        lines.forEach(function(line) {
          if (!line.startsWith('data: ')) return;
          var raw = line.slice(6).trim();
          if (!raw) return;

          var evt;
          try { evt = JSON.parse(raw); } catch (e) { return; }

          if (evt.type === 'progress') {
            cs_appendLog(evt.message);
          } else if (evt.type === 'done') {
            cs_appendLog('Done! ' + evt.shorts.length + ' short(s) built.');
            cs_renderResults(evt.shorts);
            cs_setGenerating(false);
          } else if (evt.type === 'error') {
            cs_appendLog('ERROR: ' + evt.message);
            cs_setGenerating(false);
          }
        });

        pump();
      }).catch(function(err) {
        cs_appendLog('Stream error: ' + err);
        cs_setGenerating(false);
      });
    }

    pump();
  }).catch(function(err) {
    cs_appendLog('Fetch error: ' + err);
    cs_setGenerating(false);
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cs_setGenerating(active) {
  var btn = document.getElementById('csGenerateBtn');
  if (!btn) return;
  btn.disabled = active;
  btn.textContent = active ? '⏳ Generating…' : '✂️ Generate Shorts';
}

function cs_appendLog(message) {
  var el = document.getElementById('csLog');
  if (!el) return;
  el.textContent += message + '\n';
  el.scrollTop = el.scrollHeight;
}

function cs_renderResults(shorts) {
  var container = document.getElementById('csResults');
  if (!container) return;
  container.innerHTML = '';

  if (!shorts || shorts.length === 0) {
    container.innerHTML = '<p class="text-sm text-subtext">No shorts were built.</p>';
    return;
  }

  shorts.forEach(function(s) {
    var card = document.createElement('div');
    card.className = 'hero-panel bg-surface rounded-[1.9rem] p-5 flex flex-col gap-3';

    var sceneBadge = 'Scene ' + String(s.scene_index).padStart(2, '0');
    var scoreLabel = 'Score ' + s.score + '/10';

    card.innerHTML = [
      '<div class="flex items-center gap-3 flex-wrap">',
      '  <span class="state-pill is-auto text-xs">' + sceneBadge + '</span>',
      '  <span class="text-sm font-bold text-accent">' + scoreLabel + '</span>',
      '</div>',
      '<p class="text-sm text-subtext">' + cs_escapeHtml(s.reason) + '</p>',
      '<div class="flex flex-col gap-1">',
      '  <p class="text-[10px] uppercase tracking-[0.2em] text-subtext font-semibold">Output path</p>',
      '  <p class="text-xs text-text font-mono break-all bg-base rounded-lg px-3 py-2">' + cs_escapeHtml(s.output_path) + '</p>',
      '</div>',
    ].join('');

    container.appendChild(card);
  });
}

function cs_escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Init (called by shared.js on first tab activation)
// ---------------------------------------------------------------------------

function cs_init() {
  cs_loadEpisodes();
}
