function closeDialog(result) {
  const overlay = document.getElementById('podcastDialogOverlay');
  if (!overlay || overlay.classList.contains('hidden')) return;
  overlay.classList.add('hidden');
  document.body.style.overflow = '';

  const resolver = activeDialogResolver;
  const dialogType = activeDialogType;
  activeDialogResolver = null;
  activeDialogType = null;

  if (resolver) {
    resolver(dialogType === 'alert' ? undefined : !!result);
  }
}

function setDialogTone(tone) {
  const eyebrow = document.getElementById('podcastDialogEyebrow');
  const confirmBtn = document.getElementById('podcastDialogConfirm');
  if (!eyebrow || !confirmBtn) return;

  eyebrow.className = 'text-[10px] uppercase tracking-[0.22em] text-subtext';
  confirmBtn.className = 'glass-btn px-4 py-2.5 rounded-xl font-bold';
  confirmBtn.style.removeProperty('background');
  confirmBtn.style.removeProperty('border-color');
  confirmBtn.style.removeProperty('color');
  confirmBtn.style.removeProperty('box-shadow');

  if (tone === 'danger') {
    eyebrow.textContent = 'Confirm Destructive Action';
    eyebrow.classList.add('text-rose');
    confirmBtn.classList.add('glass-btn-danger');
    confirmBtn.style.setProperty('background', 'rgba(255, 123, 139, 0.18)', 'important');
    confirmBtn.style.setProperty('border-color', 'rgba(255, 123, 139, 0.45)', 'important');
    confirmBtn.style.setProperty('color', '#fffafb', 'important');
    confirmBtn.style.setProperty('text-shadow', '0 1px 0 rgba(0, 0, 0, 0.16)', 'important');
    confirmBtn.style.setProperty('box-shadow', '0 18px 34px rgba(255, 123, 139, 0.12), 0 10px 24px rgba(0, 0, 0, 0.16)', 'important');
  } else if (tone === 'warn') {
    eyebrow.textContent = 'Confirm Action';
    eyebrow.classList.add('text-[color:var(--ui-warn)]');
    confirmBtn.classList.add('glass-btn-warn');
    confirmBtn.style.setProperty('background', 'rgba(255, 211, 107, 0.22)', 'important');
    confirmBtn.style.setProperty('border-color', 'rgba(255, 211, 107, 0.5)', 'important');
    confirmBtn.style.setProperty('color', '#090601', 'important');
    confirmBtn.style.setProperty('text-shadow', '0 1px 0 rgba(255, 255, 255, 0.12)', 'important');
    confirmBtn.style.setProperty('box-shadow', '0 18px 34px rgba(255, 211, 107, 0.12), 0 10px 24px rgba(0, 0, 0, 0.16)', 'important');
  } else {
    eyebrow.textContent = 'Heads Up';
    eyebrow.classList.add('text-accent');
    confirmBtn.classList.add('glass-btn-primary');
    confirmBtn.style.setProperty('background', 'rgba(94, 231, 255, 0.24)', 'important');
    confirmBtn.style.setProperty('border-color', 'rgba(94, 231, 255, 0.5)', 'important');
    confirmBtn.style.setProperty('color', '#031015', 'important');
    confirmBtn.style.setProperty('text-shadow', '0 1px 0 rgba(255, 255, 255, 0.12)', 'important');
    confirmBtn.style.setProperty('box-shadow', '0 18px 34px rgba(94, 231, 255, 0.12), 0 10px 24px rgba(0, 0, 0, 0.16)', 'important');
  }
}

function openDialog(options = {}) {
  const overlay = document.getElementById('podcastDialogOverlay');
  const card = document.getElementById('podcastDialogCard');
  const title = document.getElementById('podcastDialogTitle');
  const message = document.getElementById('podcastDialogMessage');
  const confirmBtn = document.getElementById('podcastDialogConfirm');
  const cancelBtn = document.getElementById('podcastDialogCancel');
  const closeBtn = document.getElementById('podcastDialogClose');

  const {
    type = 'confirm',
    title: dialogTitle = type === 'alert' ? 'Notice' : 'Are you sure?',
    message: dialogMessage = '',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    closeLabel = 'OK',
    tone = 'info',
  } = options;

  if (!overlay || !card || !title || !message || !confirmBtn || !cancelBtn || !closeBtn) {
    return Promise.resolve(type === 'alert' ? undefined : false);
  }

  if (activeDialogResolver) {
    closeDialog(false);
  }

  activeDialogType = type;
  title.textContent = dialogTitle;
  message.textContent = dialogMessage;
  confirmBtn.textContent = type === 'alert' ? closeLabel : confirmLabel;
  cancelBtn.textContent = cancelLabel;
  cancelBtn.classList.toggle('hidden', type === 'alert');
  setDialogTone(tone);

  overlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  return new Promise((resolve) => {
    activeDialogResolver = resolve;

    setTimeout(() => {
      if (type === 'alert') {
        confirmBtn.focus();
      } else {
        cancelBtn.focus();
      }
    }, 0);
  });
}

function showConfirm(options = {}) {
  return openDialog({ type: 'confirm', tone: 'warn', ...options });
}

function showAlert(options = {}) {
  return openDialog({ type: 'alert', ...options });
}
