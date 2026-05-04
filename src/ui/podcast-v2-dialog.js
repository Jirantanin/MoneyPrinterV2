function closeDialogV2(result) {
  const overlay = document.getElementById('podcastV2DialogOverlay');
  if (!overlay || overlay.classList.contains('hidden')) return;
  overlay.classList.add('hidden');
  document.body.style.overflow = '';

  const resolver = activeDialogResolverV2;
  const dialogType = activeDialogTypeV2;
  activeDialogResolverV2 = null;
  activeDialogTypeV2 = null;

  if (resolver) {
    resolver(dialogType === 'alert' ? undefined : !!result);
  }
}

function setDialogToneV2(tone) {
  const eyebrow = document.getElementById('podcastV2DialogEyebrow');
  const confirmBtn = document.getElementById('podcastV2DialogConfirm');
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

function openDialogV2(options = {}) {
  const overlay = document.getElementById('podcastV2DialogOverlay');
  const card = document.getElementById('podcastV2DialogCard');
  const title = document.getElementById('podcastV2DialogTitle');
  const message = document.getElementById('podcastV2DialogMessage');
  const confirmBtn = document.getElementById('podcastV2DialogConfirm');
  const cancelBtn = document.getElementById('podcastV2DialogCancel');
  const closeBtn = document.getElementById('podcastV2DialogClose');

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

  if (activeDialogResolverV2) {
    closeDialogV2(false);
  }

  activeDialogTypeV2 = type;
  title.textContent = dialogTitle;
  message.textContent = dialogMessage;
  confirmBtn.textContent = type === 'alert' ? closeLabel : confirmLabel;
  cancelBtn.textContent = cancelLabel;
  cancelBtn.classList.toggle('hidden', type === 'alert');
  setDialogToneV2(tone);

  overlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  return new Promise((resolve) => {
    activeDialogResolverV2 = resolve;

    setTimeout(() => {
      if (type === 'alert') {
        confirmBtn.focus();
      } else {
        cancelBtn.focus();
      }
    }, 0);
  });
}

function showConfirmV2(options = {}) {
  return openDialogV2({ type: 'confirm', tone: 'warn', ...options });
}

function showAlertV2(options = {}) {
  return openDialogV2({ type: 'alert', ...options });
}
