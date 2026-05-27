import { notFound } from "next/navigation";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Pips, Dots } from "@/components/pips";
import { ClanSigil } from "@/components/clan-sigil";
import { VisionEditor } from "@/components/vision-editor";
import { CLAN_LABEL, getKindred } from "@/lib/mock-data";

export default function EditorPage({ params }: { params: { id: string } }) {
  const k = getKindred(params.id);
  if (!k) return notFound();

  return (
    <>
      <SiteHeader domainName="St. Augustine by Night" username="storyteller_amelia" active="kindred" />

      <div className="max-w-[1440px] mx-auto px-10 pt-6 text-[11px] smallcaps text-bone-dim">
        <Link href="/" className="hover:text-gold">Kindred</Link>
        <span className="dot" />
        <Link href="/" className="hover:text-gold">{k.base.name}</Link>
        <span className="dot" />
        <span className="text-gold">New Vision</span>
      </div>

      <section className="max-w-[1440px] mx-auto px-10 mt-4">
        <Card
          className="gilded frame-gold overflow-hidden"
          style={{
            background:
              "radial-gradient(circle at 85% 50%, rgba(138,36,36,0.18), transparent 50%), radial-gradient(circle at 10% 100%, rgba(176,138,62,0.08), transparent 60%), linear-gradient(180deg, #171012 0%, #120d0f 100%)",
          }}
        >
          <div className="relative px-10 py-8">
            <div className="absolute top-6 right-10">
              <ClanSigil clan={k.base.clan} size={120} opacity={0.3} />
            </div>
            <div className="relative">
              <div className="smallcaps text-xs text-gold mb-2">
                Clan {CLAN_LABEL[k.base.clan]} · {k.base.generation}th Generation · {k.sect}
              </div>
              <h1 className="font-display text-5xl tracking-wide mb-1">{k.base.name}</h1>
              <p className="font-script italic text-lg text-bone-muted mt-1">
                &ldquo;{k.base.epithet}&rdquo; · Embraced {k.embraced} · sired by {k.sire}
              </p>

              <div className="mt-7 flex flex-wrap items-end gap-10">
                <div>
                  <div className="smallcaps text-[10px] text-bone-dim mb-2">Hunger</div>
                  <Pips filled={k.base.hunger} />
                </div>
                <div>
                  <div className="smallcaps text-[10px] text-bone-dim mb-2">Humanity · {k.base.humanity}</div>
                  <Dots filled={k.base.humanity} />
                </div>
                <div>
                  <div className="smallcaps text-[10px] text-bone-dim mb-2">Blood Potency · {k.base.bloodPotency}</div>
                  <Dots filled={k.base.bloodPotency} />
                </div>
                <div className="border-l border-ink-700 pl-10 ml-2">
                  <div className="smallcaps text-[10px] text-bone-dim mb-2">Discipline</div>
                  <div className="font-script text-base text-bone-muted italic">{k.disciplineLabel}</div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </section>

      {/* Ornamental divider */}
      <div className="max-w-[1440px] mx-auto px-10 mt-8 flex items-center gap-4">
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gold-dim to-transparent opacity-50" />
        <svg width="32" height="14" viewBox="0 0 32 14" fill="none">
          <path d="M0 7 L10 7 M22 7 L32 7" stroke="#b08a3e" strokeWidth="0.7" />
          <path d="M16 1 L19 7 L16 13 L13 7 Z" stroke="#b08a3e" strokeWidth="0.7" fill="rgba(138,36,36,0.4)" />
        </svg>
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gold-dim to-transparent opacity-50" />
      </div>

      <main className="max-w-[1440px] mx-auto px-10 pb-16 mt-8 grid grid-cols-12 gap-10">
        <aside className="col-span-4 space-y-7">
          <Card className="gilded p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display smallcaps text-sm text-gold">Active Threads</h3>
              <span className="text-[10px] text-bone-dim italic">{k.threads.length} open</span>
            </div>
            {k.threads.length ? (
              <ul className="space-y-4">
                {k.threads.map(t => (
                  <li key={t.title} className={"border-l-2 pl-4 " + (t.isPrimary ? "border-blood" : "border-gold-dim")}>
                    <div className="font-script text-xl leading-tight">{t.title}</div>
                    <div className="text-[11px] text-bone-dim mt-1 smallcaps">
                      Opened {t.whenOpened} · {t.visionsCount} vision{t.visionsCount !== 1 ? "s" : ""} inflicted
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="font-script italic text-bone-dim text-sm">No threads yet open.</p>
            )}
          </Card>

          <Card className="gilded p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display smallcaps text-sm text-gold">Recurring Symbols</h3>
              <span className="text-[10px] text-bone-dim italic">divined by Zillah</span>
            </div>
            {k.symbols.length ? (
              <div className="flex flex-wrap gap-2">
                {k.symbols.map(s => (
                  <Badge key={s.name} variant="codex" className="text-sm px-3 py-1 font-normal">
                    {s.name} <span className="text-gold text-xs ml-1">{s.count}</span>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="font-script italic text-bone-dim text-sm">No motifs have surfaced yet.</p>
            )}
          </Card>

          <Card className="gilded p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display smallcaps text-sm text-gold">From the Codex</h3>
              <a className="text-[10px] smallcaps text-bone-dim hover:text-gold" href="#">Full History →</a>
            </div>
            {k.recentVisions.length ? (
              <ul className="space-y-5">
                {k.recentVisions.map((v, i) => (
                  <li key={i} className={"border-l pl-4 " + (v.type.includes("Bleed") ? "border-blood/50" : "border-mauve")}>
                    <div className="flex items-baseline justify-between">
                      <span className={"smallcaps text-[11px] " + (v.type.includes("Bleed") ? "text-blood-bright" : "text-bone-muted")}>
                        {v.type}
                      </span>
                      <span className="text-[10px] text-bone-dim smallcaps">{v.when}</span>
                    </div>
                    <p className="font-serif text-bone-muted text-sm mt-1.5 italic leading-relaxed">{v.body}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="font-script italic text-bone-dim text-sm">No visions inflicted yet.</p>
            )}
          </Card>
        </aside>

        <section className="col-span-8 space-y-6">
          <VisionEditor k={k} />
        </section>
      </main>

      <SiteFooter />
    </>
  );
}
