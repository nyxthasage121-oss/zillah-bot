"use client";
import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { KindredCard } from "@/components/kindred-card";
import { CLAN_LABEL, type Kindred, type Clan } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export function KindredFilterBar({ roster }: { roster: Kindred[] }) {
  const [clan, setClan] = useState<Clan | "all">("all");
  const [q, setQ] = useState("");

  const tallies = useMemo(() => {
    const m: Record<string, number> = {};
    roster.forEach(k => { m[k.clan] = (m[k.clan] || 0) + 1; });
    return m;
  }, [roster]);

  const filtered = useMemo(() => roster.filter(k => {
    if (clan !== "all" && k.clan !== clan) return false;
    if (q && !(`${k.name} ${k.epithet} ${CLAN_LABEL[k.clan]}`.toLowerCase().includes(q.toLowerCase()))) return false;
    return true;
  }), [roster, clan, q]);

  const FilterBtn = ({ value, label }: { value: Clan | "all"; label: string }) => (
    <Button
      variant="codex"
      size="sm"
      onClick={() => setClan(value)}
      className={cn(
        "smallcaps text-[10px] h-auto px-3 py-1.5 rounded-sm",
        clan === value && "border-gold text-bone bg-gradient-to-b from-gold/10 to-gold/0"
      )}
    >
      {label}
    </Button>
  );

  return (
    <>
      <div className="flex items-end justify-between mb-2">
        <div>
          <div className="smallcaps text-[11px] text-gold">Domain Roster</div>
          <h1 className="font-display text-5xl tracking-wide mt-1">The Kindred</h1>
          <p className="font-script italic text-bone-muted mt-2 text-lg">
            {roster.length} soul{roster.length !== 1 ? "s" : ""} inscribed in your chronicle
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Input
            placeholder="Search by name, clan, sire…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-72 font-serif"
          />
          <Button variant="codex" size="sm" className="smallcaps text-[11px] px-4 py-2.5 h-auto">+ New Kindred</Button>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-6 mb-8 flex-wrap">
        <span className="smallcaps text-[10px] text-bone-dim mr-3">Filter by clan</span>
        <FilterBtn value="all" label={`All · ${roster.length}`} />
        {(Object.keys(CLAN_LABEL) as Clan[]).filter(c => tallies[c]).map(c => (
          <FilterBtn key={c} value={c} label={`${CLAN_LABEL[c]} · ${tallies[c]}`} />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {filtered.map(k => <KindredCard key={k.id} k={k} />)}
      </div>
    </>
  );
}
