const PODCAST_V2_SETTINGS_STORAGE_KEY = 'mpv2_podcast_v2_system_settings_v1';
const PODCAST_V2_SETTINGS_DEFAULTS = {
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
const PODCAST_V2_SETTINGS_TOOLTIPS = {
  'voices.english_edge_voice': 'เน€เธชเธตเธขเธ Edge เธ—เธตเนเธเธฐเนเธเนเน€เธเนเธเธเนเธฒเน€เธฃเธดเนเธกเธ•เนเธเน€เธงเธฅเธฒเธชเธฃเนเธฒเธเธเธญเธ"เนเธเธชเธ•เนเธ เธฒเธฉเธฒเธญเธฑเธเธเธคเธฉ',
  'voices.english_edge_rate': 'เธเธงเธฒเธกเน€เธฃเนเธงเน€เธชเธตเธขเธเธ เธฒเธฉเธฒเธญเธฑเธเธเธคเธฉเธเธญเธ Edge เธเนเธฒเน€เธเนเธเน€เธเธญเธฃเนเน€เธเนเธเธ•เน เน€เธเนเธ +10% เธซเธฃเธทเธญ -12%',
  'voices.thai_edge_voice': 'เน€เธชเธตเธขเธ Edge เธซเธฅเธฑเธเธชเธณเธซเธฃเธฑเธเธเธญเธ"เนเธเธชเธ•เนเธ เธฒเธฉเธฒเนเธ—เธข',
  'voices.thai_edge_rate': 'เธเธงเธฒเธกเน€เธฃเนเธงเน€เธชเธตเธขเธเธ เธฒเธฉเธฒเนเธ—เธขเธเธญเธ Edge เนเธเนเธ•เธญเธเน€เธฅเธทเธญเธ Thai + Edge เนเธฅเธฐเธ•เธญเธ fallback เธกเธฒ Edge',
  'voices.thai_elevenlabs_voice_id': 'Voice ID เธเนเธฒเน€เธฃเธดเนเธกเธ•เนเธเธเธญเธ ElevenLabs เธชเธณเธซเธฃเธฑเธเธ เธฒเธฉเธฒเนเธ—เธข เธ–เนเธฒ voice เธเธตเนเนเธเนเนเธกเนเนเธ"เน pipeline เนเธ—เธขเนเธเธ ElevenLabs เธเธฐเธเธฑเธเธซเธฃเธทเธญ fallback',
  'voices.thai_gemini_voice': 'ชื่อเสียง Gemini TTS ที่ใช้ตอน Thai + Gemini เช่น Aoede, Puck, Charon, Kore, Fenrir, Zephyr',
  'models.script_model': 'เนเธกเน€เธ"เธฅเธเนเธญเธเธงเธฒเธกเธซเธฅเธฑเธเธชเธณเธซเธฃเธฑเธ flow generate script เธเธญเธ podcast เน€เธฅเธทเธญเธเน€เธเนเธ Claude, MiniMax เธซเธฃเธทเธญ Ollama เนเธ"เน',
  'models.ollama_model': 'เนเธกเน€เธ"เธฅ Ollama เธซเธฅเธฑเธเธ—เธตเนเนเธเนเธ•เธญเธ generate script เนเธฅเธฐเธเธฒเธเธเนเธญเธเธงเธฒเธกเธเธฑเนเธ local',
  'models.minimax_model': 'เนเธกเน€เธ"เธฅ MiniMax เธ—เธตเนเธเธฐเนเธเนเน€เธกเธทเนเธญเธฃเธฐเธเธเน€เธฅเธทเธญเธ provider เธเธตเนเธชเธณเธซเธฃเธฑเธเธเธฒเธเธเนเธญเธเธงเธฒเธก',
  'models.anthropic_model': 'เธเธทเนเธญเนเธกเน€เธ"เธฅ Anthropic/Claude เธ—เธตเนเธเธฐเนเธเนเน€เธกเธทเนเธญ script model เธ–เธนเธเธ•เธฑเนเธเน€เธเนเธเธ•เธฃเธฐเธเธนเธฅ claude',
  'models.image_model': 'เนเธกเน€เธ"เธฅเธชเธฃเนเธฒเธเธ เธฒเธเธซเธฅเธฑเธเธชเธณเธซเธฃเธฑเธ scene images เนเธฅเธฐ thumbnail generation',
  'models.image_aspect_ratio': 'เธญเธฑเธ•เธฃเธฒเธชเนเธงเธเธ เธฒเธเน€เธฃเธดเนเธกเธ•เนเธเธเธญเธเธ เธฒเธเธ—เธตเนเธชเธฃเนเธฒเธเนเธซเธกเน เน€เธเนเธ 16:9 เธชเธณเธซเธฃเธฑเธ podcast เธเธเธ•เธด',
  'prompting.narrator_persona': 'เธเธธเธเธฅเธดเธเธเธญเธเธเธนเนเน€เธฅเนเธฒเน€เธฃเธทเนเธญเธ เน€เธเนเธ เธเธฃเธดเธเธเธฑเธ เธฅเธถเธเธฅเธฑเธ เธซเธฃเธทเธญเน€เธเนเธเธเธฑเธเน€เธญเธ เธเนเธฒเธเธตเนเธ–เธนเธเธชเนเธเน€เธเนเธฒ prompt เธ•เธญเธเน€เธเธตเธขเธเธชเธเธฃเธดเธเธ•เน',
  'prompting.podcast_style_prompt': 'เธชเนเธ•เธฅเนเธ เธฒเธเธซเธฅเธฑเธเธ—เธตเนเธ–เธนเธเน€เธ•เธดเธกเธ•เนเธญเธ—เนเธฒเธข image prompt เน€เธเธทเธญเธเธ—เธธเธ scene',
  'prompting.script_system_prompt': 'system prompt เธชเธณเธซเธฃเธฑเธเธเธฒเธฃเน€เธเธตเธขเธเธชเธเธฃเธดเธเธ•เน podcast เนเธเนเธเธธเธกเนเธ—เธ เธฃเธนเธเนเธเธ เนเธฅเธฐเธเนเธญเธเธฑเธเธเธฑเธเธเธญเธ output',
  'prompting.metadata_system_prompt': 'system prompt เธชเธณเธซเธฃเธฑเธ title, description เนเธฅเธฐ tags เธเธญเธเธเธฅเธดเธ',
  'prompting.thumbnail_system_prompt': 'system prompt เธชเธณเธซเธฃเธฑเธเธชเธฃเนเธฒเธเธ เธฒเธ thumbnail เนเธฅเธฐเธ—เธดเธจเธ—เธฒเธเธเธญเธเธ เธฒเธเธเธ',
  'advanced.image_retry_count': 'เธเธณเธเธงเธเธเธฃเธฑเนเธเธ—เธตเนเธฃเธฐเธเธเธเธฐเธฅเธญเธเธชเธฃเนเธฒเธเธ เธฒเธเนเธซเธกเนเธญเธฑเธ•เนเธเธกเธฑเธ•เธดเน€เธกเธทเนเธญ image generation fail',
  'advanced.audio_retry_count': 'เธเธณเธเธงเธเธเธฃเธฑเนเธเธ—เธตเนเธฃเธฐเธเธเธเธฐเธฅเธญเธเธชเธฃเนเธฒเธเน€เธชเธตเธขเธเนเธซเธกเนเธญเธฑเธ•เนเธเธกเธฑเธ•เธดเน€เธกเธทเนเธญ TTS fail เธซเธฃเธทเธญเนเธ"เนเนเธเธฅเนเน€เธชเธตเธขเธเนเธกเนเธชเธกเธเธนเธฃเธ"เน',
  'advanced.script_sentence_length': 'เธเธณเธเธงเธเธเธฃเธฐเนเธขเธเนเธ"เธขเธเธฃเธฐเธกเธฒเธ"เธ•เนเธญ scene เธ—เธตเนเนเธเนเน€เธเนเธเน€เธเนเธฒเธซเธกเธฒเธขเธ•เธญเธ generate script',
};

function clonePodcastSettingsV2(settings = PODCAST_V2_SETTINGS_DEFAULTS) {
  return JSON.parse(JSON.stringify(settings));
}

function isPlainObjectV2(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function deepMergePodcastSettingsV2(target, source) {
  if (!isPlainObjectV2(source)) return target;
  Object.keys(source).forEach((key) => {
    const sourceValue = source[key];
    if (sourceValue === undefined || sourceValue === null || sourceValue === '') return;
    if (isPlainObjectV2(target[key]) && isPlainObjectV2(sourceValue)) {
      deepMergePodcastSettingsV2(target[key], sourceValue);
    } else {
      target[key] = sourceValue;
    }
  });
  return target;
}

function normalizePodcastSettingsV2(raw) {
  const source = raw?.settings || raw?.data || raw || {};
  const merged = clonePodcastSettingsV2();
  return deepMergePodcastSettingsV2(merged, source);
}

function getPodcastSettingByPathV2(settings, path) {
  return path.split('.').reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), settings);
}

function setPodcastSettingByPathV2(settings, path, value) {
  const parts = path.split('.');
  let cursor = settings;
  for (let i = 0; i < parts.length - 1; i++) {
    const part = parts[i];
    if (!isPlainObjectV2(cursor[part])) cursor[part] = {};
    cursor = cursor[part];
  }
  cursor[parts[parts.length - 1]] = value;
}

function podcastSettingsSelectOptionsV2(selectEl, values) {
  if (!selectEl || selectEl.dataset.optionsReady === 'true') return;
  selectEl.innerHTML = values
    .map((value) => `<option value="${value}">${value}</option>`)
    .join('');
  selectEl.dataset.optionsReady = 'true';
}

function initPodcastSettingsTooltipsV2() {
  document.querySelectorAll('#podcastV2SettingsForm [data-setting-path]').forEach((field) => {
    const helpText = PODCAST_V2_SETTINGS_TOOLTIPS[field.dataset.settingPath];
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

function populatePodcastSettingsOptionsV2() {
  podcastSettingsSelectOptionsV2(document.getElementById('podcastV2EnglishEdgeRate'), ['+20%', '+10%', '+5%', '0%', '-5%', '-8%', '-10%', '-12%', '-15%', '-20%', '-25%']);
  podcastSettingsSelectOptionsV2(document.getElementById('podcastV2ThaiEdgeRate'), ['+20%', '+10%', '+5%', '0%', '-5%', '-8%', '-10%', '-12%', '-15%', '-20%', '-25%']);
  podcastSettingsSelectOptionsV2(document.getElementById('podcastV2ImageAspectRatio'), ['16:9', '9:16', '1:1', '4:3', '3:4']);
  podcastSettingsSelectOptionsV2(document.getElementById('podcastV2ImageRetryCount'), ['1', '2', '3', '4', '5']);
  podcastSettingsSelectOptionsV2(document.getElementById('podcastV2AudioRetryCount'), ['1', '2', '3', '4', '5']);
  podcastSettingsSelectOptionsV2(document.getElementById('podcastV2ScriptSentenceLength'), ['2', '3', '4', '5', '6', '7', '8']);
}

function readPodcastSettingsFormV2() {
  const settings = clonePodcastSettingsV2();
  document.querySelectorAll('#podcastV2SettingsForm [data-setting-path]').forEach((el) => {
    const value = el.tagName === 'TEXTAREA' ? el.value : el.value.trim();
    setPodcastSettingByPathV2(settings, el.dataset.settingPath, value);
  });
  return settings;
}

function writePodcastSettingsFormV2(settings) {
  const source = normalizePodcastSettingsV2(settings);
  document.querySelectorAll('#podcastV2SettingsForm [data-setting-path]').forEach((el) => {
    const value = getPodcastSettingByPathV2(source, el.dataset.settingPath);
    el.value = value === undefined || value === null ? '' : String(value);
  });
  updatePodcastSettingsSummaryV2(source);
}

function updatePodcastSettingsSummaryV2(settings = podcastV2SystemSettings || PODCAST_V2_SETTINGS_DEFAULTS) {
  const summary = document.getElementById('podcastV2SettingsSummary');
  if (!summary) return;
  const source = normalizePodcastSettingsV2(settings);
  summary.textContent =
    `Defaults: EN ${source.voices.english_edge_voice} ${source.voices.english_edge_rate} · ` +
    `TH ${source.voices.thai_edge_voice} ${source.voices.thai_edge_rate} · ` +
    `Script ${source.models.script_model} · Image ${source.models.image_model}`;
}

function getPodcastSystemSettingsPayloadV2() {
  return normalizePodcastSettingsV2(podcastV2SystemSettings || clonePodcastSettingsV2());
}

async function loadPodcastSettingsV2() {
  if (podcastV2SettingsLoadPromise) return podcastV2SettingsLoadPromise;
  podcastV2SettingsLoadPromise = (async () => {
    populatePodcastSettingsOptionsV2();
    let loaded = null;

    try {
      const res = await fetch('/api/settings/podcast');
      if (res.ok) {
        loaded = normalizePodcastSettingsV2(await res.json());
      }
    } catch (_) {}

    if (!loaded) {
      try {
        const cached = localStorage.getItem(PODCAST_V2_SETTINGS_STORAGE_KEY);
        if (cached) loaded = normalizePodcastSettingsV2(JSON.parse(cached));
      } catch (_) {}
    }

    if (!loaded) {
      loaded = clonePodcastSettingsV2();
    }

    podcastV2SystemSettings = loaded;
    writePodcastSettingsFormV2(loaded);
    return loaded;
  })();

  try {
    return await podcastV2SettingsLoadPromise;
  } finally {
    podcastV2SettingsLoadPromise = null;
  }
}

function showPodcastSettingsStatusV2(message, tone = 'muted') {
  const status = document.getElementById('podcastV2SettingsStatus');
  if (!status) return;
  status.className = `text-sm ${tone === 'error' ? 'text-rose' : tone === 'success' ? 'text-accent' : tone === 'warn' ? 'text-[color:var(--ui-warn)]' : 'text-subtext'}`;
  status.textContent = message;
}

function closePodcastSettingsV2() {
  const overlay = document.getElementById('podcastV2SettingsOverlay');
  if (!overlay || overlay.classList.contains('hidden')) return;
  overlay.classList.add('hidden');
  document.body.style.overflow = '';
}

async function openPodcastSettingsV2() {
  populatePodcastSettingsOptionsV2();
  showPodcastSettingsStatusV2('Loading system settings...', 'muted');
  await loadPodcastSettingsV2();
  const overlay = document.getElementById('podcastV2SettingsOverlay');
  overlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  showPodcastSettingsStatusV2('Edit defaults here. Changes apply to future generation and regenerated assets.', 'muted');
}

async function savePodcastSettingsV2() {
  const draft = readPodcastSettingsFormV2();
  podcastV2SystemSettings = normalizePodcastSettingsV2(draft);
  writePodcastSettingsFormV2(podcastV2SystemSettings);

  try {
    const res = await fetch('/api/settings/podcast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(podcastV2SystemSettings),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      throw new Error(data.error || 'Save failed');
    }
    const confirmed = normalizePodcastSettingsV2(data.settings || data);
    podcastV2SystemSettings = confirmed;
    writePodcastSettingsFormV2(confirmed);
    try {
      localStorage.setItem(PODCAST_V2_SETTINGS_STORAGE_KEY, JSON.stringify(confirmed));
    } catch (_) {}
    showPodcastSettingsStatusV2('Saved system settings.', 'success');
    updatePodcastSettingsSummaryV2(confirmed);
  } catch (err) {
    try {
      localStorage.setItem(PODCAST_V2_SETTINGS_STORAGE_KEY, JSON.stringify(podcastV2SystemSettings));
      showPodcastSettingsStatusV2(`Saved locally because the settings API is unavailable: ${err.message}`, 'warn');
      updatePodcastSettingsSummaryV2(podcastV2SystemSettings);
    } catch (_) {
      showPodcastSettingsStatusV2(`Save failed: ${err.message}`, 'error');
    }
  }
}

function resetPodcastSettingsToDefaultsV2() {
  podcastV2SystemSettings = clonePodcastSettingsV2();
  writePodcastSettingsFormV2(podcastV2SystemSettings);
  showPodcastSettingsStatusV2('Reset to default values. Save to keep them.', 'warn');
  try {
    localStorage.setItem(PODCAST_V2_SETTINGS_STORAGE_KEY, JSON.stringify(podcastV2SystemSettings));
  } catch (_) {}
}
