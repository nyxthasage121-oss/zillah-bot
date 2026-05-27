import Link from "next/link";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function SiteHeader({ domainName, username, active }: { domainName?: string; username?: string; active?: string }) {
  return (
    <header className="border-b border-ink-700">
      <div className="max-w-[1440px] mx-auto px-10 h-16 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="#b08a3e" strokeWidth="0.7" />
            <circle cx="16" cy="16" r="10" stroke="#b08a3e" strokeWidth="0.4" />
            <path d="M16 4 L16 28 M4 16 L28 16 M7 7 L25 25 M25 7 L7 25" stroke="#b08a3e" strokeWidth="0.4" />
            <circle cx="16" cy="16" r="2.5" fill="#8a2424" stroke="#d4a94d" strokeWidth="0.5" />
          </svg>
          <div className="leading-tight">
            <div className="font-display tracking-[0.2em] text-xl">ZILLAH</div>
            <div className="smallcaps text-[10px] text-gold">Storyteller&apos;s Codex</div>
          </div>
          {domainName && (
            <div className="ml-6 pl-6 border-l border-ink-700">
              <div className="smallcaps text-[10px] text-bone-dim">Domain</div>
              <div className="font-script text-base text-bone">{domainName}</div>
            </div>
          )}
        </div>
        <nav className="flex items-center gap-7 text-sm text-bone-muted">
          <Link className={"smallcaps text-xs hover:text-bone " + (active === "kindred" ? "text-gold" : "")} href="/">Kindred</Link>
          <Link className="smallcaps text-xs hover:text-bone" href="#">Drafts <span className="text-gold">3</span></Link>
          <Link className="smallcaps text-xs hover:text-bone" href="#">Threads</Link>
          <Link className="smallcaps text-xs hover:text-bone" href="#">Chronicle</Link>
          <span className="w-px h-5 bg-ink-700" />
          {username && (
            <span className="flex items-center gap-2">
              <Avatar><AvatarFallback>{username[0].toUpperCase()}</AvatarFallback></Avatar>
              <span className="text-bone-muted">{username}</span>
            </span>
          )}
        </nav>
      </div>
    </header>
  );
}
