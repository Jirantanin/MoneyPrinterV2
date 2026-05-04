const PODCAST_SETTINGS_STORAGE_KEY = 'mpv2_podcast_system_settings_v1';
const PODCAST_SETTINGS_DEFAULTS = {
  voices: {
    english_edge_voice: 'en-US-ChristopherNeural',
    english_edge_rate: '+20%',
    thai_edge_voice: 'th-TH-PremwadeeNeural',
    thai_edge_rate: '-12%',
    thai_elevenlabs_voice_id: 'NNl6r8mD7vthiJatiJt1',
    thai_gemini_voice: 'Aoede',
  },
  models: {
    script_model: 'claude-sonnet-4-6',
    ollama_model: 'qwen3:8b',
    minimax_model: 'minimax/minimax-m2.5',
    anthropic_model: 'claude-sonnet-4-6',
    image_model: 'gemini-2.5-flash-image',
    image_aspect_ratio: '16:9',
  },
  prompting: {
    narrator_persona: 'A curious and engaging narrator who explains complex topics clearly',
    podcast_style_prompt: 'cinematic documentary illustration, single coherent scene, no comic panels, no superhero styling, no exaggerated heroic poses, no named characters unless explicitly requested, restrained realistic composition, moody lighting, subtle texture, thoughtful atmosphere --',
    script_system_prompt: 'You are {narrator_name}, {narrator_persona}. /no_think Narrate in {language} language. Narrate in a compelling storytelling voice. Output ONLY valid JSON matching the provided schema. No markdown, no asterisks, no extra commentary.',
    metadata_system_prompt: 'You are a YouTube metadata writer for long-form podcast videos.\n\nWrite ALL metadata in {language}.\nIf {language} is Thai, the title, description, hashtags, and tags must be in Thai except unavoidable proper nouns.\nDo not switch to English unless the source topic itself is a proper noun, branded term, or official mission name.\n\nTopic: {topic}\nOpening narration: {opening_narration}\n\n{creative_direction_block}Generate YouTube metadata for this podcast episode. Return ONLY valid JSON with title, description, and tags.',
    thumbnail_system_prompt: 'YouTube thumbnail for a podcast episode about: {topic}. {creative_direction_block}Single dramatic scene, no comic panels, no borders, no gutters. Dark cinematic mood, bold colors, high contrast. One striking central subject that fills the frame. Photorealistic or painterly illustration style. No text, no logos.',
  },
  advanced: {
    image_retry_count: '3',
    audio_retry_count: '3',
    script_sentence_length: '4',
  },
};
const PODCAST_SETTINGS_TOOLTIPS = {
  'voices.english_edge_voice': 'เน€เธชเธตเธขเธ Edge เธ—เธตเนเธเธฐเนเธเนเน€เธเนเธเธเนเธฒเน€เธฃเธดเนเธกเธ•เนเธเน€เธงเธฅเธฒเธชเธฃเนเธฒเธเธเธญเธ”เนเธเธชเธ•เนเธ เธฒเธฉเธฒเธญเธฑเธเธเธคเธฉ',
  'voices.english_edge_rate': 'เธเธงเธฒเธกเน€เธฃเนเธงเน€เธชเธตเธขเธเธ เธฒเธฉเธฒเธญเธฑเธเธเธคเธฉเธเธญเธ Edge เธเนเธฒเน€เธเนเธเน€เธเธญเธฃเนเน€เธเนเธเธ•เน เน€เธเนเธ +10% เธซเธฃเธทเธญ -12%',
  'voices.thai_edge_voice': 'เน€เธชเธตเธขเธ Edge เธซเธฅเธฑเธเธชเธณเธซเธฃเธฑเธเธเธญเธ”เนเธเธชเธ•เนเธ เธฒเธฉเธฒเนเธ—เธข',
  'voices.thai_edge_rate': 'เธเธงเธฒเธกเน€เธฃเนเธงเน€เธชเธตเธขเธเธ เธฒเธฉเธฒเนเธ—เธขเธเธญเธ Edge เนเธเนเธ•เธญเธเน€เธฅเธทเธญเธ Thai + Edge เนเธฅเธฐเธ•เธญเธ fallback เธกเธฒ Edge',
  'voices.thai_elevenlabs_voice_id': 'Voice ID เธเนเธฒเน€เธฃเธดเนเธกเธ•เนเธเธเธญเธ ElevenLabs เธชเธณเธซเธฃเธฑเธเธ เธฒเธฉเธฒเนเธ—เธข เธ–เนเธฒ voice เธเธตเนเนเธเนเนเธกเนเนเธ”เน pipeline เนเธ—เธขเนเธเธ ElevenLabs เธเธฐเธเธฑเธเธซเธฃเธทเธญ fallback',
  'voices.thai_gemini_voice': 'ชื่อเสียง Gemini TTS ที่ใช้ตอน Thai + Gemini เช่น Aoede, Puck, Charon, Kore, Fenrir, Zephyr',
  'models.script_model': 'เนเธกเน€เธ”เธฅเธเนเธญเธเธงเธฒเธกเธซเธฅเธฑเธเธชเธณเธซเธฃเธฑเธ flow generate script เธเธญเธ podcast เน€เธฅเธทเธญเธเน€เธเนเธ Claude, MiniMax เธซเธฃเธทเธญ Ollama เนเธ”เน',
  'models.ollama_model': 'เนเธกเน€เธ”เธฅ Ollama เธซเธฅเธฑเธเธ—เธตเนเนเธเนเธ•เธญเธ generate script เนเธฅเธฐเธเธฒเธเธเนเธญเธเธงเธฒเธกเธเธฑเนเธ local',
  'models.minimax_model': 'เนเธกเน€เธ”เธฅ MiniMax เธ—เธตเนเธเธฐเนเธเนเน€เธกเธทเนเธญเธฃเธฐเธเธเน€เธฅเธทเธญเธ provider เธเธตเนเธชเธณเธซเธฃเธฑเธเธเธฒเธเธเนเธญเธเธงเธฒเธก',
  'models.anthropic_model': 'เธเธทเนเธญเนเธกเน€เธ”เธฅ Anthropic/Claude เธ—เธตเนเธเธฐเนเธเนเน€เธกเธทเนเธญ script model เธ–เธนเธเธ•เธฑเนเธเน€เธเนเธเธ•เธฃเธฐเธเธนเธฅ claude',
  'models.image_model': 'เนเธกเน€เธ”เธฅเธชเธฃเนเธฒเธเธ เธฒเธเธซเธฅเธฑเธเธชเธณเธซเธฃเธฑเธ scene images เนเธฅเธฐ thumbnail generation',
  'models.image_aspect_ratio': 'เธญเธฑเธ•เธฃเธฒเธชเนเธงเธเธ เธฒเธเน€เธฃเธดเนเธกเธ•เนเธเธเธญเธเธ เธฒเธเธ—เธตเนเธชเธฃเนเธฒเธเนเธซเธกเน เน€เธเนเธ 16:9 เธชเธณเธซเธฃเธฑเธ podcast เธเธเธ•เธด',
  'prompting.narrator_persona': 'เธเธธเธเธฅเธดเธเธเธญเธเธเธนเนเน€เธฅเนเธฒเน€เธฃเธทเนเธญเธ เน€เธเนเธ เธเธฃเธดเธเธเธฑเธ เธฅเธถเธเธฅเธฑเธ เธซเธฃเธทเธญเน€เธเนเธเธเธฑเธเน€เธญเธ เธเนเธฒเธเธตเนเธ–เธนเธเธชเนเธเน€เธเนเธฒ prompt เธ•เธญเธเน€เธเธตเธขเธเธชเธเธฃเธดเธเธ•เน',
  'prompting.podcast_style_prompt': 'เธชเนเธ•เธฅเนเธ เธฒเธเธซเธฅเธฑเธเธ—เธตเนเธ–เธนเธเน€เธ•เธดเธกเธ•เนเธญเธ—เนเธฒเธข image prompt เน€เธเธทเธญเธเธ—เธธเธ scene',
  'prompting.script_system_prompt': 'system prompt เธชเธณเธซเธฃเธฑเธเธเธฒเธฃเน€เธเธตเธขเธเธชเธเธฃเธดเธเธ•เน podcast เนเธเนเธเธธเธกเนเธ—เธ เธฃเธนเธเนเธเธ เนเธฅเธฐเธเนเธญเธเธฑเธเธเธฑเธเธเธญเธ output',
  'prompting.metadata_system_prompt': 'system prompt เธชเธณเธซเธฃเธฑเธ title, description เนเธฅเธฐ tags เธเธญเธเธเธฅเธดเธ',
  'prompting.thumbnail_system_prompt': 'system prompt เธชเธณเธซเธฃเธฑเธเธชเธฃเนเธฒเธเธ เธฒเธ thumbnail เนเธฅเธฐเธ—เธดเธจเธ—เธฒเธเธเธญเธเธ เธฒเธเธเธ',
  'advanced.image_retry_count': 'เธเธณเธเธงเธเธเธฃเธฑเนเธเธ—เธตเนเธฃเธฐเธเธเธเธฐเธฅเธญเธเธชเธฃเนเธฒเธเธ เธฒเธเนเธซเธกเนเธญเธฑเธ•เนเธเธกเธฑเธ•เธดเน€เธกเธทเนเธญ image generation fail',
  'advanced.audio_retry_count': 'เธเธณเธเธงเธเธเธฃเธฑเนเธเธ—เธตเนเธฃเธฐเธเธเธเธฐเธฅเธญเธเธชเธฃเนเธฒเธเน€เธชเธตเธขเธเนเธซเธกเนเธญเธฑเธ•เนเธเธกเธฑเธ•เธดเน€เธกเธทเนเธญ TTS fail เธซเธฃเธทเธญเนเธ”เนเนเธเธฅเนเน€เธชเธตเธขเธเนเธกเนเธชเธกเธเธนเธฃเธ“เน',
  'advanced.script_sentence_length': 'เธเธณเธเธงเธเธเธฃเธฐเนเธขเธเนเธ”เธขเธเธฃเธฐเธกเธฒเธ“เธ•เนเธญ scene เธ—เธตเนเนเธเนเน€เธเนเธเน€เธเนเธฒเธซเธกเธฒเธขเธ•เธญเธ generate script',
};
function clonePodcastSettings(settings = PODCAST_SETTINGS_DEFAULTS) {
  return JSON.parse(JSON.stringify(settings));
}

function isPlainObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function deepMergePodcastSettings(target, source) {
  if (!isPlainObject(source)) return target;
  Object.keys(source).forEach((key) => {
    const sourceValue = source[key];
    if (sourceValue === undefined || sourceValue === null || sourceValue === '') return;
    if (isPlainObject(target[key]) && isPlainObject(sourceValue)) {
      deepMergePodcastSettings(target[key], sourceValue);
    } else {
      target[key] = sourceValue;
    }
  });
  return target;
}

function normalizePodcastSettings(raw) {
  const source = raw?.settings || raw?.data || raw || {};
  const merged = clonePodcastSettings();
  return deepMergePodcastSettings(merged, source);
}

function getPodcastSettingByPath(settings, path) {
  return path.split('.').reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), settings);
}

function setPodcastSettingByPath(settings, path, value) {
  const parts = path.split('.');
  let cursor = settings;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (!isPlainObject(cursor[part])) cursor[part] = {};
    cursor = cursor[part];
  }
  cursor[parts[parts.length - 1]] = value;
}

function podcastSettingsSelectOptions(selectEl, values) {
  if (!selectEl || selectEl.dataset.optionsReady === 'true') return;
  selectEl.innerHTML = values
    .map((value) => `<option value="${value}">${value}</option>`)
    .join('');
  selectEl.dataset.optionsReady = 'true';
}

function initPodcastSettingsTooltips() {
  document.querySelectorAll('#podcastSettingsForm [data-setting-path]').forEach((field) => {
    const helpText = PODCAST_SETTINGS_TOOLTIPS[field.dataset.settingPath];
    if (!helpText) return;
    const label = field.closest('label');
    const labelText = label?.querySelector('span');
    if (!labelText || labelText.dataset.tooltipReady === 'true') return;

    labelText.classList.add('setting-label-with-help');

    const help = document.createElement('span');
    help.className = 'setting-help';

    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'setting-help-trigger';
    trigger.setAttribute('aria-label', `Explain ${labelText.textContent.trim()}`);

    const dot = document.createElement('span');
    dot.className = 'setting-help-dot';
    dot.textContent = 'i';

    const bubble = document.createElement('span');
    bubble.className = 'setting-help-bubble';
    bubble.textContent = helpText;

    trigger.appendChild(dot);
    help.appendChild(trigger);
    help.appendChild(bubble);
    labelText.appendChild(help);
    labelText.dataset.tooltipReady = 'true';
  });
}

function populatePodcastSettingsOptions() {
  podcastSettingsSelectOptions(document.getElementById('podcastEnglishEdgeRate'), ['+20%', '+10%', '+5%', '0%', '-5%', '-8%', '-10%', '-12%', '-15%', '-20%', '-25%']);
  podcastSettingsSelectOptions(document.getElementById('podcastThaiEdgeRate'), ['+20%', '+10%', '+5%', '0%', '-5%', '-8%', '-10%', '-12%', '-15%', '-20%', '-25%']);
  podcastSettingsSelectOptions(document.getElementById('podcastImageAspectRatio'), ['16:9', '9:16', '1:1', '4:3', '3:4']);
  podcastSettingsSelectOptions(document.getElementById('podcastImageRetryCount'), ['1', '2', '3', '4', '5']);
  podcastSettingsSelectOptions(document.getElementById('podcastAudioRetryCount'), ['1', '2', '3', '4', '5']);
  podcastSettingsSelectOptions(document.getElementById('podcastScriptSentenceLength'), ['2', '3', '4', '5', '6', '7', '8']);
}

function readPodcastSettingsForm() {
  const settings = clonePodcastSettings();
  document.querySelectorAll('#podcastSettingsForm [data-setting-path]').forEach((el) => {
    const value = el.tagName === 'TEXTAREA' ? el.value : el.value.trim();
    setPodcastSettingByPath(settings, el.dataset.settingPath, value);
  });
  return settings;
}

function writePodcastSettingsForm(settings) {
  const source = normalizePodcastSettings(settings);
  document.querySelectorAll('#podcastSettingsForm [data-setting-path]').forEach((el) => {
    const value = getPodcastSettingByPath(source, el.dataset.settingPath);
    el.value = value === undefined || value === null ? '' : String(value);
  });
  updatePodcastSettingsSummary(source);
}

function updatePodcastSettingsSummary(settings = podcastSystemSettings || PODCAST_SETTINGS_DEFAULTS) {
  const summary = document.getElementById('podcastSettingsSummary');
  if (!summary) return;
  const source = normalizePodcastSettings(settings);
  summary.textContent =
    `Defaults: EN ${source.voices.english_edge_voice} ${source.voices.english_edge_rate} ยท ` +
    `TH ${source.voices.thai_edge_voice} ${source.voices.thai_edge_rate} ยท ` +
    `Script ${source.models.script_model} ยท Image ${source.models.image_model}`;
}

function getPodcastSystemSettingsPayload() {
  return normalizePodcastSettings(podcastSystemSettings || clonePodcastSettings());
}

async function loadPodcastSettings() {
  if (podcastSettingsLoadPromise) return podcastSettingsLoadPromise;
  podcastSettingsLoadPromise = (async () => {
    populatePodcastSettingsOptions();
    let loaded = null;

    try {
      const res = await fetch('/api/settings/podcast');
      if (res.ok) {
        loaded = normalizePodcastSettings(await res.json());
      }
    } catch (_) {}

    if (!loaded) {
      try {
        const cached = localStorage.getItem(PODCAST_SETTINGS_STORAGE_KEY);
        if (cached) loaded = normalizePodcastSettings(JSON.parse(cached));
      } catch (_) {}
    }

    if (!loaded) {
      loaded = clonePodcastSettings();
    }

    podcastSystemSettings = loaded;
    writePodcastSettingsForm(loaded);
    return loaded;
  })();

  try {
    return await podcastSettingsLoadPromise;
  } finally {
    podcastSettingsLoadPromise = null;
  }
}

function showPodcastSettingsStatus(message, tone = 'muted') {
  const status = document.getElementById('podcastSettingsStatus');
  if (!status) return;
  status.className = `text-sm ${tone === 'error' ? 'text-rose' : tone === 'success' ? 'text-accent' : tone === 'warn' ? 'text-[color:var(--ui-warn)]' : 'text-subtext'}`;
  status.textContent = message;
}

function closePodcastSettings() {
  const overlay = document.getElementById('podcastSettingsOverlay');
  if (!overlay || overlay.classList.contains('hidden')) return;
  overlay.classList.add('hidden');
  document.body.style.overflow = '';
}

async function openPodcastSettings() {
  populatePodcastSettingsOptions();
  showPodcastSettingsStatus('Loading system settings...', 'muted');
  await loadPodcastSettings();
  const overlay = document.getElementById('podcastSettingsOverlay');
  overlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  showPodcastSettingsStatus('Edit defaults here. Changes apply to future generation and regenerated assets.', 'muted');
}

async function savePodcastSettings() {
  const draft = readPodcastSettingsForm();
  podcastSystemSettings = normalizePodcastSettings(draft);
  writePodcastSettingsForm(podcastSystemSettings);

  try {
    const res = await fetch('/api/settings/podcast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(podcastSystemSettings),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Save failed');
    }
    const confirmed = normalizePodcastSettings(data.settings || data);
    podcastSystemSettings = confirmed;
    writePodcastSettingsForm(confirmed);
    try {
      localStorage.setItem(PODCAST_SETTINGS_STORAGE_KEY, JSON.stringify(confirmed));
    } catch (_) {}
    showPodcastSettingsStatus('Saved system settings.', 'success');
    updatePodcastSettingsSummary(confirmed);
  } catch (err) {
    try {
      localStorage.setItem(PODCAST_SETTINGS_STORAGE_KEY, JSON.stringify(podcastSystemSettings));
      showPodcastSettingsStatus(`Saved locally because the settings API is unavailable: ${err.message}`, 'warn');
      updatePodcastSettingsSummary(podcastSystemSettings);
    } catch (_) {
      showPodcastSettingsStatus(`Save failed: ${err.message}`, 'error');
    }
  }
}

function resetPodcastSettingsToDefaults() {
  podcastSystemSettings = clonePodcastSettings();
  writePodcastSettingsForm(podcastSystemSettings);
  showPodcastSettingsStatus('Reset to default values. Save to keep them.', 'warn');
  try {
    localStorage.setItem(PODCAST_SETTINGS_STORAGE_KEY, JSON.stringify(podcastSystemSettings));
  } catch (_) {}
}

// -------------------------------------------------------------------------
// Init: render steps on page load
// -------------------------------------------------------------------------
