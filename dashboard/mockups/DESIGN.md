# Zillah Codex — Design System

A portable reference for the look used in the v2 vision-editor mockup.
Everything here is plain HTML/CSS + Tailwind via CDN; lift any piece into
another project.

> Pairs with **`dashboard/STACK.md`** (the architecture + Python/JS recipe).
> This doc covers the visual half; that doc covers the structural half.

---

## 1 · Fonts

Four families, three jobs.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700&family=Cormorant+Garamond:wght@400;500;600;700&family=EB+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

| Family | Role | When to use |
|---|---|---|
| **Cinzel** | Display headings, small-caps labels | Page titles, section headings, button labels, anything ALL CAPS / tracked-out |
| **Cormorant Garamond** | Decorative serif | Character names, subtitles, dropdown values — anywhere you want a "script-feel" but legible |
| **EB Garamond** (italic supported) | Body prose | Vision text, italicized excerpts — anything readable and narrative |
| **Inter** | UI chrome | Nav, microcopy, default body — neutral background voice |

---

## 2 · Color tokens (Tailwind config)

```js
tailwind.config = {
  theme: {
    extend: {
      colors: {
        ink:    { 950: '#0a0708', 900: '#120d0f', 850: '#171012', 800: '#1f1618', 700: '#2a1f22' },
        bone:   { DEFAULT: '#ece4d6', muted: '#c9bfb0', dim: '#8b8275' },
        blood:  { DEFAULT: '#8a2424', bright: '#b03030', deep: '#3a1418' },
        gold:   { DEFAULT: '#b08a3e', bright: '#d4a94d', dim: '#7a5e29' },
        mauve:  { DEFAULT: '#4a3d44', dim: '#352b30' },
      },
      fontFamily: {
        display: ['"Cinzel"', 'serif'],
        script:  ['"Cormorant Garamond"', 'serif'],
        serif:   ['"EB Garamond"', 'serif'],
        sans:    ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
}
```

**Rules of thumb**
- `ink-950` is the page background. Everything else is layered above.
- `bone` is your primary text. **Never use pure white** — too harsh against the warm dark.
- `gold` is the ambient accent: borders, section headers, inline emphasis, sigils.
- `blood` is reserved for **destructive or irreversible actions only** — Send button, deletes, hunger pips. Don't waste it on hover states.
- `mauve` is for subtle dividers and dim metadata; barely visible by design.

---

## 3 · Body & atmosphere

Three layered effects make the page feel "lit" rather than flat black.

```css
body {
  background-color: #0a0708;
  color: #ece4d6;
  background-image:
    radial-gradient(ellipse 1200px 600px at 50% -200px, rgba(138, 36, 36, 0.18), transparent 60%),
    radial-gradient(ellipse 800px 400px at 100% 100%, rgba(176, 138, 62, 0.06), transparent 60%);
}

/* Film grain — most of the texture comes from this */
body::before {
  content: "";
  position: fixed; inset: 0;
  pointer-events: none;
  z-index: 100;
  opacity: 0.06;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
  mix-blend-mode: overlay;
}

/* Vignette — pulls the eye to centre */
body::after {
  content: "";
  position: fixed; inset: 0;
  pointer-events: none;
  z-index: 99;
  background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%);
}
```

The grain is the secret ingredient. Without it the page looks like a flat
design comp; with it the page looks *photographed*.

---

## 4 · Surfaces — the "gilded" card

The card style that does all the heavy lifting:

```css
.gilded {
  background:
    linear-gradient(180deg, rgba(176,138,62,0.04) 0%, rgba(176,138,62,0) 30%),
    linear-gradient(180deg, #171012 0%, #120d0f 100%);
  border: 1px solid #2a1f22;
  box-shadow:
    inset 0 0 0 1px rgba(176,138,62,0.05),  /* faint gold inner */
    inset 0 1px 0 rgba(236, 228, 214, 0.03), /* top highlight */
    0 30px 60px -20px rgba(0,0,0,0.6);       /* depth drop */
}

/* Inset / sunken variant — for inputs and selects */
.gilded-inset {
  background:
    linear-gradient(180deg, rgba(0,0,0,0.25) 0%, rgba(0,0,0,0) 40%),
    #120d0f;
  border: 1px solid #2a1f22;
  box-shadow: inset 0 1px 6px rgba(0,0,0,0.6);
}

/* Double-line "framed" treatment — a 6px-inset second border in gold */
.frame-gold { position: relative; }
.frame-gold::before {
  content: "";
  position: absolute;
  inset: 6px;
  border: 1px solid rgba(176,138,62,0.25);
  pointer-events: none;
}
```

**Pattern**: every meaningful container gets `.gilded`. Only the *most
important* container on the page (hero banner, primary editor) also gets
`.frame-gold` on top of it. Don't stack frames everywhere or the page
starts to feel like a Victorian wedding invitation.

---

## 5 · Typography utilities

```css
/* The single most-used utility — small-caps labels with tracked letters */
.smallcaps {
  font-variant: all-small-caps;
  letter-spacing: 0.16em;
}

/* Drop cap for narrative prose */
.dropcap::first-letter {
  font-family: 'Cinzel', serif;
  font-weight: 600;
  float: left;
  font-size: 3.4em;
  line-height: 0.85;
  padding: 0.18em 0.18em 0 0;
  color: #b08a3e;
  text-shadow: 0 1px 0 rgba(0,0,0,0.6);
}

/* Dot separator for inline metadata */
.dot::before { content: "·"; margin: 0 0.6rem; color: #4a3d44; }
```

**Pattern**: every metadata label is `<span class="smallcaps text-[10px] gold-text">...</span>`.
That single combination — tiny + tracked + gold — is what makes the UI
feel like an old book.

---

## 6 · Buttons

```css
.btn-send {
  background: linear-gradient(180deg, #b03030 0%, #8a2424 100%);
  color: #f5ede0;
  border: 1px solid #d4a94d;
  box-shadow:
    inset 0 1px 0 rgba(255,200,160,0.25),
    inset 0 -1px 0 rgba(0,0,0,0.4),
    0 6px 18px -6px rgba(176,48,48,0.55);
  text-shadow: 0 1px 0 rgba(0,0,0,0.4);
}

.btn-ghost {
  border: 1px solid #2a1f22;
  color: #c9bfb0;
  background: rgba(18,13,15,0.5);
}
.btn-ghost:hover { border-color: #b08a3e; color: #ece4d6; }
```

Use button labels in `smallcaps` + Cinzel. Don't sentence-case them.

---

## 7 · Small components

### "Pip" (Hunger / V:TM-style stat)
```css
.pip {
  width: 14px; height: 14px;
  border: 1px solid #b08a3e;
  transform: rotate(45deg);
  display: inline-block;
}
.pip.filled {
  background: linear-gradient(135deg, #b03030, #5a1010);
  border-color: #d4a94d;
  box-shadow: inset 0 0 4px rgba(255,180,140,0.4);
}
```

### "Dot" (Humanity / Blood Potency / generic dot meter)
```css
.hdot {
  width: 11px; height: 11px;
  border-radius: 50%;
  border: 1px solid #b08a3e;
  display: inline-block;
}
.hdot.filled {
  background: radial-gradient(circle at 35% 30%, #f0e0c0 0%, #b08a3e 60%, #6a4f1e 100%);
}
```

### Chip (toggleable tag)
```css
.chip {
  border: 1px solid #2a1f22;
  color: #c9bfb0;
  background: rgba(18,13,15,0.6);
}
.chip[aria-selected="true"] {
  border-color: #b03030;
  color: #ece4d6;
  background: linear-gradient(180deg, rgba(138,36,36,0.18), rgba(138,36,36,0.06));
  box-shadow: inset 0 0 0 1px rgba(176,138,62,0.18);
}
```

---

## 8 · Ornamental divider

Drop this anywhere you'd otherwise put a hairline `<hr>`:

```html
<div class="flex items-center gap-4">
  <div class="flex-1 h-px bg-gradient-to-r from-transparent via-gold-dim to-transparent opacity-50"></div>
  <svg width="32" height="14" viewBox="0 0 32 14" fill="none">
    <path d="M0 7 L10 7 M22 7 L32 7" stroke="#b08a3e" stroke-width="0.7"/>
    <path d="M16 1 L19 7 L16 13 L13 7 Z" stroke="#b08a3e" stroke-width="0.7" fill="rgba(138,36,36,0.4)"/>
  </svg>
  <div class="flex-1 h-px bg-gradient-to-r from-transparent via-gold-dim to-transparent opacity-50"></div>
</div>
```

---

## 9 · Microcopy voice

The visual design works because the *language* matches it. Some rules:

- **Verbs are dramatic, not neutral.** "Inflict" not "Send". "Inscribe" not
  "Save". "Bid Claude" not "Generate".
- **Time is poetic.** "9 nights past" not "9 days ago". "Moments ago" is fine.
- **Section names are nouns of consequence.** "The Codex", "The Kindred",
  "Recurring Symbols", not "History", "Players", "Tags".
- **Confirmations earn a beat.** "Once inflicted, the night cannot be
  unwritten." A neutral admin app would say "Are you sure?".
- **Lowercase italics for asides.** Anything in *italics* feels like a
  margin note in a leather journal. Use it for hints and metadata.

If you strip the gilded surfaces and gold accents but keep this voice,
the design still feels right. If you keep the surfaces and write "Submit
Form" — it falls apart immediately.

---

## 10 · Restraint rules

The thing that makes this not-kitsch:

1. **One accent color does the dramatic work.** Blood red is for danger
   and finality. Gold is the ambient tone. Don't introduce a third unless
   you have a reason.
2. **Ornament is rationed.** The hero banner is framed. Section cards
   are *not*. If everything is ornamental, nothing is.
3. **No drop shadows on text.** Except the drop cap.
4. **No corner radius above 2px** anywhere. `rounded-sm` only. Sharpness
   reads as expensive; rounded reads as SaaS.
5. **Margins are generous.** A gothic UI breathes. Cramming kills it.
6. **No emoji.** Use inline SVG sigils. Emoji break the spell instantly.

---

## 11 · Stack used

- **Tailwind CSS via CDN** (`https://cdn.tailwindcss.com`) with the inline
  `tailwind.config` above
- **Google Fonts** (Cinzel + Cormorant Garamond + EB Garamond + Inter)
- **Vanilla JS** for interactivity — no framework
- **Inline SVG** for sigils, dividers, icons — no icon library

Total external dependencies: 2 (Tailwind CDN, Google Fonts). Both can be
inlined for offline use.
