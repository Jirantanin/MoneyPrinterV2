// shared.js — Tab switching logic shared by podcast, shorts, and clip-shorts components.
// Loaded in <head> so switchTab() is available before DOMContentLoaded.

var shorts_initialized = false;
var clip_shorts_initialized = false;

function switchTab(tab) {
  var tabs = ['podcast', 'shorts', 'clip_shorts', 'podcast_v2'];
  tabs.forEach(function(t) {
    document.getElementById('tab-' + t).classList.toggle('hidden', t !== tab);
    var btn = document.getElementById('tab-btn-' + t);
    btn.classList.toggle('border-accent', t === tab);
    btn.classList.toggle('text-accent', t === tab);
    btn.classList.toggle('border-transparent', t !== tab);
    btn.classList.toggle('text-subtext', t !== tab);
    btn.dataset.tabActive = t === tab ? 'true' : 'false';
  });
  if (tab === 'shorts' && !shorts_initialized) {
    shorts_initialized = true;
    shorts_loadAccounts();
    shorts_loadRecentShorts();
  }
  if (tab === 'clip_shorts' && !clip_shorts_initialized) {
    clip_shorts_initialized = true;
    if (typeof cs_init === 'function') cs_init();
  }
}

// Initialize on load — default to Podcast tab
document.addEventListener('DOMContentLoaded', function() {
  switchTab('podcast');
});
