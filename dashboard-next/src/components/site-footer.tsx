export function SiteFooter() {
  return (
    <footer className="border-t border-ink-700 mt-12">
      <div className="max-w-[1440px] mx-auto px-10 py-5 flex items-center justify-between text-[11px] text-bone-dim">
        <span className="smallcaps">Zillah · the Codex</span>
        <svg width="60" height="14" viewBox="0 0 60 14" fill="none">
          <path d="M0 7 L24 7 M36 7 L60 7" stroke="#b08a3e" strokeWidth="0.6" />
          <path d="M30 1 L33 7 L30 13 L27 7 Z" stroke="#b08a3e" strokeWidth="0.6" fill="rgba(138,36,36,0.4)" />
        </svg>
        <span className="smallcaps">The night is long</span>
      </div>
    </footer>
  );
}
