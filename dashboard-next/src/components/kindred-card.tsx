import Link from "next/link";
import { CLAN_LABEL, type Kindred } from "@/lib/mock-data";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Pips, Dots } from "@/components/pips";
import { ClanSigil } from "@/components/clan-sigil";

const CLAN_TEXT: Record<string, string> = {
  toreador: "text-gold-bright",
  tremere: "text-blood-bright",
  malkavian: "text-[#8a4ab0]",
  salubri: "text-bone-muted",
  hecata: "text-[#6a8a4a]",
  banuhaqim: "text-[#4a8a8a]",
};

export function KindredCard({ k }: { k: Kindred }) {
  return (
    <Link href={`/kindred/${k.id}`} className="block group" data-clan={k.clan}>
      <Card className="gilded p-6 transition-all duration-200 group-hover:border-gold group-hover:-translate-y-0.5 group-hover:shadow-[inset_0_0_0_1px_rgba(176,138,62,0.15),0_30px_60px_-20px_rgba(176,48,48,0.35)]">
        <div className="flex items-start justify-between">
          <div>
            <div className={"smallcaps text-[10px] " + (CLAN_TEXT[k.clan] || "")}>
              {CLAN_LABEL[k.clan]} · {k.generation}th Gen
            </div>
            <h3 className="font-display text-2xl tracking-wide mt-1">{k.name}</h3>
            <p className="font-script italic text-bone-muted text-sm mt-1">{k.epithet}</p>
          </div>
          <ClanSigil clan={k.clan} size={32} />
        </div>

        <div className="mt-5 pt-4 border-t border-ink-700 grid grid-cols-2 gap-3 text-[10px] smallcaps text-bone-dim">
          <div>
            <div className="mb-1">Hunger</div>
            <Pips filled={k.hunger} />
          </div>
          <div>
            <div className="mb-1">Humanity · {k.humanity}</div>
            <Dots filled={k.humanity} />
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-ink-700 text-[11px] text-bone-muted leading-relaxed">
          <div className="flex items-baseline justify-between">
            <span className="italic">Last vision · {k.lastVisionWhen}</span>
            <Badge variant={k.lastVisionType.includes("Bleed") ? "bleed" : "codex"} className="smallcaps text-[10px]">
              {k.lastVisionType}
            </Badge>
          </div>
          <div className="mt-2 italic">
            {k.threadsCount} active thread{k.threadsCount !== 1 ? "s" : ""}
            {" · "}
            {k.draftsCount ? `${k.draftsCount} unsent draft${k.draftsCount !== 1 ? "s" : ""}` : "no drafts"}
          </div>
        </div>
      </Card>
    </Link>
  );
}
