// Alpine bootstrap for the Codex.
// Defines the toast store, the combobox component, and the editor component.
// All page-level interactivity goes through Alpine; HTMX handles server roundtrips.

// HTMX → toast: any response with an X-Codex-Toast header surfaces that
// message via the Alpine toast store. Keeps the wire format trivial — no
// JSON body required for save/delete/inflict round-trips.
document.addEventListener('htmx:afterRequest', (e) => {
  const msg = e.detail.xhr.getResponseHeader('X-Codex-Toast');
  if (msg && window.Alpine?.store('toast')) {
    Alpine.store('toast').show(msg);
  }
});

document.addEventListener('alpine:init', () => {
  // --- Toast store (Sonner-style stack) -------------------------------------
  Alpine.store('toast', {
    messages: [],
    _next: 1,
    show(msg, ms = 2400) {
      const id = this._next++;
      this.messages.push({ id, msg, gone: false });
      setTimeout(() => {
        const m = this.messages.find(x => x.id === id);
        if (m) m.gone = true;
        setTimeout(() => {
          this.messages = this.messages.filter(x => x.id !== id);
        }, 300);
      }, ms);
    },
  });

  // --- Combobox component ---------------------------------------------------
  Alpine.data('combobox', (options, initial) => ({
    open: false,
    selected: initial,
    options,
    highlighted: 0,
    toggle() {
      this.open = !this.open;
      if (this.open) this.highlighted = Math.max(0, this.options.indexOf(this.selected));
    },
    close() { this.open = false; },
    select(opt) {
      this.selected = opt;
      this.open = false;
    },
    onKey(e) {
      if (e.key === 'Escape') return this.close();
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (!this.open) return (this.open = true);
        this.highlighted = (this.highlighted + 1) % this.options.length;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (!this.open) return (this.open = true);
        this.highlighted = (this.highlighted - 1 + this.options.length) % this.options.length;
      }
      if (e.key === 'Enter' && this.open) {
        e.preventDefault();
        this.select(this.options[this.highlighted]);
      }
    },
  }));

  // --- Vision editor component ---------------------------------------------
  Alpine.data('visionEditor', (initial) => ({
    type: initial.type,
    body: initial.body || '',
    drafts: initial.drafts || [],
    loadedDraftId: '',
    bidding: false,
    showInflict: false,
    dirty: false,
    savedLabel: 'Draft auto-inscribed · moments ago',

    get chars() { return this.body.length; },
    get seconds() { return Math.max(1, Math.round(this.chars / 22)); },

    init() {
      // Auto-save indicator loop
      setInterval(() => {
        if (this.dirty) {
          this.dirty = false;
          this.savedLabel = 'Draft auto-inscribed · moments ago';
        }
      }, 2000);

      // Keyboard shortcuts
      window.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 's') {
          e.preventDefault();
          this.saveDraft();
        }
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
          e.preventDefault();
          this.showInflict = true;
        }
        if (e.key === 'Escape') this.showInflict = false;
      });
    },

    onInput() {
      this.dirty = true;
      this.savedLabel = 'Inscribing…';
    },

    loadDraftFrom(el) {
      // Reads the draft straight off the <li>'s data-* attributes — keeps
      // the source of truth in the server-rendered partial that HTMX swaps.
      if (!el) return;
      this.type = el.dataset.visionType;
      this.body = el.dataset.body;
      this.loadedDraftId = el.dataset.draftId;
      Alpine.store('toast').show('Draft loaded · ' + this.type);
    },

    saveDraft() { Alpine.store('toast').show('Draft inscribed in the Codex'); },
    schedule()  { Alpine.store('toast').show('Scheduled · will inflict at sundown'); },
    preview()   { Alpine.store('toast').show('Preview opens in Discord (not yet wired)'); },

    inflict() {
      this.showInflict = false;
      Alpine.store('toast').show('Vision inflicted · delivered to Discord');
    },

    async bidClaude() {
      const sampleDrafts = [
        "Tonight, every wineglass you pass holds a single red moth at its bottom, drowned and unmoving. The waiters notice nothing. When you lift one to your own table, the moth, very slowly, opens its wings.",
        "The woman in white is at your elbow before you hear her arrive. She does not speak. She places, on the marble in front of you, a small mirror. Your reflection in it is wearing a different coat than the one you have on tonight — the coat you wore the night you were Embraced.",
        "Somewhere beneath the city a violin is being tuned. You feel each adjustment as a small pull behind your sternum. When the player finally begins, you recognise the piece: it is the song you composed for Vittoria, the year she made you, and which you have told no one of since.",
      ];
      this.bidding = true;
      this.body = '';
      const draft = sampleDrafts[Math.floor(Math.random() * sampleDrafts.length)];
      for (const ch of draft) {
        this.body += ch;
        this.dirty = true;
        await new Promise(r => setTimeout(r, 14 + Math.random() * 18));
      }
      this.bidding = false;
    },
  }));

  // --- Kindred roster filter ------------------------------------------------
  Alpine.data('kindredRoster', () => ({
    clan: 'all',
    query: '',
    matches(card) {
      if (this.clan !== 'all' && card.dataset.clan !== this.clan) return false;
      if (this.query && !card.textContent.toLowerCase().includes(this.query.toLowerCase())) return false;
      return true;
    },
    apply() {
      this.$root.querySelectorAll('a.kindred-card').forEach(c => {
        c.style.display = this.matches(c) ? '' : 'none';
      });
    },
  }));
});
