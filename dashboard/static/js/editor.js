// Vision editor: chip selection, draft loading, char count, Hunger toggle,
// Save/Schedule/Preview toasts, Inflict confirm modal, Claude-draft typing
// simulation. Real backend wiring (POST /drafts, POST /inflict) replaces
// the toasts in step 4 of the dashboard build.
document.addEventListener('DOMContentLoaded', () => {
  const chips = $$('.chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.removeAttribute('aria-selected'));
      chip.setAttribute('aria-selected', 'true');
    });
  });

  const textarea = $('.vision-input');
  const meta = textarea ? textarea.closest('.gilded').querySelector('.border-t.rule') : null;
  function updateCount() {
    if (!textarea || !meta) return;
    const len = textarea.value.length;
    const seconds = Math.max(1, Math.round(len / 22));
    const left = meta.querySelector('div');
    if (left) {
      left.innerHTML =
        `<span><span class="gold-text font-medium">${len}</span> characters</span>` +
        `<span class="dot"></span>` +
        `<span>≈ ${seconds} seconds aloud</span>`;
    }
  }
  if (textarea) {
    textarea.addEventListener('input', updateCount);
    updateCount();
  }

  // Auto-save indicator stub
  const saveIndicator = $('[data-save-indicator]');
  let dirty = false;
  if (textarea) {
    textarea.addEventListener('input', () => {
      dirty = true;
      if (saveIndicator) saveIndicator.textContent = 'Inscribing…';
    });
    setInterval(() => {
      if (dirty) {
        dirty = false;
        if (saveIndicator) saveIndicator.textContent = 'Draft auto-inscribed · moments ago';
      }
    }, 2000);
  }

  // Drafts → editor
  $$('.draft-row').forEach(row => {
    row.addEventListener('click', () => {
      const type = row.dataset.type;
      const body = row.dataset.body;
      chips.forEach(c => {
        if (c.textContent.trim() === type) c.setAttribute('aria-selected', 'true');
        else c.removeAttribute('aria-selected');
      });
      if (textarea) {
        textarea.value = body;
        updateCount();
      }
      showToast('Draft loaded · ' + type);
      if (textarea) textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

  // Hunger pips toggle
  $$('.pip').forEach((pip, i, arr) => {
    pip.addEventListener('click', () => {
      const filled = pip.classList.contains('filled');
      arr.forEach((p, j) => {
        if (j <= i && !filled) p.classList.add('filled');
        else if (j > i) p.classList.remove('filled');
        else if (j === i && filled) p.classList.remove('filled');
      });
    });
  });

  // Ghost buttons → toasts (real handlers come with the drafts table)
  $$('.btn-ghost').forEach(b => {
    const label = b.textContent.trim();
    b.addEventListener('click', () => {
      if (label === 'Save Draft') showToast('Draft inscribed in the Codex');
      else if (label === 'Schedule for Sundown') showToast('Scheduled · will inflict at sundown');
      else if (label === 'Preview in Discord') showToast('Preview opens in Discord (not yet wired)');
    });
  });

  // Bid Claude to draft (simulated typing)
  const claudeBtn = Array.from(document.querySelectorAll('button')).find(
    b => b.textContent.trim().startsWith('Bid Claude to draft')
  );
  const sampleDrafts = [
    "Tonight, every wineglass you pass holds a single red moth at its bottom, drowned and unmoving. The waiters notice nothing. When you lift one to your own table, the moth, very slowly, opens its wings.",
    "The woman in white is at your elbow before you hear her arrive. She does not speak. She places, on the marble in front of you, a small mirror. Your reflection in it is wearing a different coat than the one you have on tonight — the coat you wore the night you were Embraced.",
    "Somewhere beneath the city a violin is being tuned. You feel each adjustment as a small pull behind your sternum. When the player finally begins, you recognise the piece: it is the song you composed for Vittoria, the year she made you, and which you have told no one of since."
  ];
  if (claudeBtn && textarea) {
    claudeBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      const originalHTML = claudeBtn.innerHTML;
      claudeBtn.disabled = true;
      claudeBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" class="animate-spin"><path d="M8 1 L9.5 6.5 L15 8 L9.5 9.5 L8 15 L6.5 9.5 L1 8 L6.5 6.5 Z" fill="#b08a3e"/></svg> Bidding…';
      const draft = sampleDrafts[Math.floor(Math.random() * sampleDrafts.length)];
      textarea.value = '';
      textarea.classList.add('typing-cursor');
      for (let i = 0; i < draft.length; i++) {
        textarea.value += draft[i];
        updateCount();
        await new Promise(r => setTimeout(r, 14 + Math.random() * 18));
      }
      textarea.classList.remove('typing-cursor');
      claudeBtn.disabled = false;
      claudeBtn.innerHTML = originalHTML;
    });
  }

  // Inflict → modal
  const backdrop = $('#modal-backdrop');
  function openModal() { backdrop && backdrop.classList.add('show'); }
  function closeModal() { backdrop && backdrop.classList.remove('show'); }
  const inflictBtn = Array.from(document.querySelectorAll('.btn-send')).find(
    b => b.textContent.trim() === 'Inflict This Vision'
  );
  if (inflictBtn) inflictBtn.addEventListener('click', openModal);
  const cancelBtn = $('#modal-cancel');
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
  const confirmBtn = $('#modal-confirm');
  if (confirmBtn) confirmBtn.addEventListener('click', () => {
    closeModal();
    showToast('Vision inflicted · delivered to Discord');
  });
  if (backdrop) {
    backdrop.addEventListener('click', e => { if (e.target === backdrop) closeModal(); });
  }
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal();
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') openModal();
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      showToast('Draft inscribed in the Codex');
    }
  });

  // Selects → toast
  $$('select').forEach(s => {
    s.addEventListener('change', () => {
      showToast(s.options[s.selectedIndex].text + ' selected');
    });
  });
});
