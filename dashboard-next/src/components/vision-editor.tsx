"use client";
import { useState, useMemo } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";
import { VISION_TYPES, SAMPLE_AI_DRAFTS, type KindredDetail, type Draft } from "@/lib/mock-data";

export function VisionEditor({ k }: { k: KindredDetail }) {
  const firstName = k.base.name.split(" ")[0];
  const [type, setType] = useState<string>("Resonance Bleed");
  const [body, setBody] = useState("");
  const [thread, setThread] = useState(k.threads[0]?.title ?? "— unaligned —");
  const [tone, setTone] = useState("Sensuous");
  const [bidding, setBidding] = useState(false);

  const chars = body.length;
  const seconds = Math.max(1, Math.round(chars / 22));

  function loadDraft(d: Draft) {
    setType(d.type);
    setBody(d.body);
    toast("Draft loaded · " + d.type);
  }

  async function bidClaude() {
    setBidding(true);
    setBody("");
    const draft = SAMPLE_AI_DRAFTS[Math.floor(Math.random() * SAMPLE_AI_DRAFTS.length)];
    let acc = "";
    for (const ch of draft) {
      acc += ch;
      setBody(acc);
      await new Promise(r => setTimeout(r, 14 + Math.random() * 18));
    }
    setBidding(false);
  }

  return (
    <>
      <div className="flex items-baseline justify-between">
        <div>
          <div className="smallcaps text-[11px] text-gold">Act of Auspex</div>
          <h2 className="font-display text-4xl tracking-wide mt-1">Compose a Vision</h2>
        </div>
        <div className="text-right">
          <div className="text-xs text-bone-dim italic">Draft auto-inscribed · moments ago</div>
          <div className="smallcaps text-[10px] text-gold-dim mt-1">⌘S to save · ⌘↵ to inflict</div>
        </div>
      </div>

      <Card className="gilded p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="smallcaps text-[11px] text-gold">Nature of the Vision</p>
          <span className="text-[10px] text-bone-dim italic">9 forms known to Auspex</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {VISION_TYPES.map(vt => (
            <Button
              key={vt}
              variant="codex"
              size="sm"
              onClick={() => setType(vt)}
              className={cn(
                "smallcaps text-[11px] h-auto px-3 py-2 rounded-sm",
                type === vt && "border-blood-bright text-bone bg-gradient-to-b from-blood/20 to-blood/5 shadow-[inset_0_0_0_1px_rgba(176,138,62,0.18)]"
              )}
            >
              {vt}
            </Button>
          ))}
        </div>
      </Card>

      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-3">
          <span className="smallcaps text-[11px] text-gold">Thread</span>
          <Select value={thread} onValueChange={setThread}>
            <SelectTrigger className="w-[260px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              {k.threads.map(t => <SelectItem key={t.title} value={t.title}>{t.title}</SelectItem>)}
              <SelectItem value="— unaligned —">— unaligned —</SelectItem>
              <SelectItem value="new">+ open a new thread…</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-3">
          <span className="smallcaps text-[11px] text-gold">Tone</span>
          <Select value={tone} onValueChange={setTone}>
            <SelectTrigger className="w-[200px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Sensuous">Sensuous</SelectItem>
              <SelectItem value="Ominous">Ominous</SelectItem>
              <SelectItem value="Cryptic">Cryptic</SelectItem>
              <SelectItem value="Beautiful / cruel">Beautiful / cruel</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card className="gilded frame-gold">
        <div className="px-7 pt-5 pb-3 flex items-center justify-between text-xs text-bone-dim border-b border-ink-700">
          <div className="flex items-center gap-4">
            <span className="smallcaps text-gold">Vision Text</span>
            <span className="italic">narrated to {firstName} in second person</span>
          </div>
          <Button variant="ghost" size="sm" className="text-bone-dim hover:text-gold-bright smallcaps text-[11px] gap-2 h-auto" onClick={bidClaude} disabled={bidding}>
            <Sparkles className={cn("h-3 w-3 text-gold", bidding && "animate-spin")} />
            {bidding ? "Bidding…" : "Bid Claude to draft"}
          </Button>
        </div>
        <div className="px-8 py-7">
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Begin the vision here. Draw from the Codex on the left…"
            rows={13}
            className="font-serif text-lg dropcap leading-[1.75]"
          />
        </div>
        <div className="px-7 py-3 border-t border-ink-700 flex items-center justify-between text-xs text-bone-dim">
          <div>
            <span><span className="text-gold font-medium">{chars}</span> characters</span>
            <span className="dot" />
            <span>≈ {seconds} seconds aloud</span>
          </div>
          <div className="italic">*italics* render in Discord</div>
        </div>
      </Card>

      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-3">
          <Button variant="codex" size="sm" className="smallcaps text-[11px] px-4 py-2.5 h-auto" onClick={() => toast("Draft inscribed in the Codex")}>
            Save Draft
          </Button>
          <Button variant="codex" size="sm" className="smallcaps text-[11px] px-4 py-2.5 h-auto" onClick={() => toast("Scheduled · will inflict at sundown")}>
            Schedule for Sundown
          </Button>
          <Button variant="codex" size="sm" className="smallcaps text-[11px] px-4 py-2.5 h-auto" onClick={() => toast("Preview opens in Discord (mockup)")}>
            Preview in Discord
          </Button>
        </div>
        <div className="flex items-center gap-5">
          <span className="text-[11px] text-bone-dim italic">Once inflicted, the night cannot be unwritten.</span>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="inflict" size="lg" className="smallcaps text-xs px-7 py-3 rounded-sm tracking-widest h-auto">
                Inflict This Vision
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <div className="smallcaps text-[10px] text-gold mb-2">Confirm the Working</div>
                <DialogTitle>Inflict this vision?</DialogTitle>
                <DialogDescription>
                  Once delivered to {k.base.name}, the vision becomes part of the chronicle.
                  The night cannot be unwritten, and the Codex will remember.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="codex" size="sm" className="smallcaps text-[11px] h-auto px-5 py-2.5">Withdraw</Button>
                <Button variant="inflict" size="sm" className="smallcaps text-xs px-6 py-2.5 tracking-widest h-auto" onClick={() => toast("Vision inflicted · delivered to Discord")}>
                  Yes, inflict it
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card className="gilded p-6 mt-4">
        <div className="flex items-baseline justify-between mb-4">
          <h3 className="font-display smallcaps text-sm text-gold">Drafts for {firstName}</h3>
          <span className="text-[10px] text-bone-dim italic">{k.drafts.length} unsent</span>
        </div>
        {k.drafts.length === 0 ? (
          <p className="font-script italic text-bone-dim text-sm">No drafts in the Codex yet.</p>
        ) : (
          <ul className="divide-y divide-ink-700">
            {k.drafts.map(d => (
              <li
                key={d.id}
                onClick={() => loadDraft(d)}
                className="py-3 flex items-baseline justify-between hover:bg-blood-deep/10 px-2 -mx-2 cursor-pointer rounded-sm"
              >
                <div className="flex-1 pr-6">
                  <Badge variant={d.type.includes("Bleed") ? "bleed" : "codex"} className="smallcaps text-[10px] mr-3">
                    {d.type}
                  </Badge>
                  <span className="font-serif italic text-bone-muted">
                    {d.body.slice(0, 96)}{d.body.length > 96 ? "…" : ""}
                  </span>
                </div>
                <span className="text-[10px] text-bone-dim smallcaps shrink-0">{d.when}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
