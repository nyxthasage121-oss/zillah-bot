// Same shape as the FastAPI dashboard's dashboard/data.py.
// Swap for real fetches when wiring backend.

export type Clan = "toreador" | "tremere" | "malkavian" | "salubri" | "hecata" | "banuhaqim";

export const CLAN_LABEL: Record<Clan, string> = {
  toreador: "Toreador",
  tremere: "Tremere",
  malkavian: "Malkavian",
  salubri: "Salubri",
  hecata: "Hecata",
  banuhaqim: "Banu Haqim",
};

export interface Kindred {
  id: string;
  name: string;
  epithet: string;
  clan: Clan;
  generation: number;
  hunger: number;
  humanity: number;
  bloodPotency: number;
  lastVisionType: string;
  lastVisionWhen: string;
  threadsCount: number;
  draftsCount: number;
}

export interface Thread { title: string; whenOpened: string; visionsCount: number; isPrimary?: boolean; }
export interface Symbol { name: string; count: number; }
export interface Vision { type: string; when: string; body: string; }
export interface Draft { id: string; type: string; body: string; when: string; }

export interface KindredDetail {
  base: Kindred;
  sire: string;
  embraced: string;
  sect: string;
  disciplineLabel: string;
  threads: Thread[];
  symbols: Symbol[];
  recentVisions: Vision[];
  drafts: Draft[];
}

export const VISION_TYPES = [
  "Standard Vision", "Lucid Vision", "Glitch Vision", "Echo Vision",
  "Resonance Bleed", "Nightmare Bleed", "The Witness", "The Warning",
  "Retrocognition Surge",
] as const;

export const ROSTER: Kindred[] = [
  { id: "100000000000000001", name: "Lucien Marchetti", epithet: "The Rose of the Ponte Vecchio", clan: "toreador", generation: 8, hunger: 3, humanity: 6, bloodPotency: 3, lastVisionType: "Resonance Bleed", lastVisionWhen: "2 nights past", threadsCount: 2, draftsCount: 3 },
  { id: "100000000000000002", name: "Yseult Vasquez",   epithet: "Regent of Chapter House Castile", clan: "tremere", generation: 9, hunger: 1, humanity: 5, bloodPotency: 4, lastVisionType: "The Warning", lastVisionWhen: "6 nights past", threadsCount: 1, draftsCount: 1 },
  { id: "100000000000000003", name: "Cassiel", epithet: "no surname remembered · the Cobwalker", clan: "malkavian", generation: 7, hunger: 4, humanity: 3, bloodPotency: 5, lastVisionType: "Nightmare Bleed", lastVisionWhen: "last night", threadsCount: 4, draftsCount: 0 },
  { id: "100000000000000004", name: "Aurelio Cortés", epithet: "Master of the Belmont Theatre", clan: "toreador", generation: 11, hunger: 2, humanity: 7, bloodPotency: 2, lastVisionType: "Echo Vision", lastVisionWhen: "4 nights past", threadsCount: 1, draftsCount: 2 },
  { id: "100000000000000005", name: "Sister Magdalene", epithet: "of the Giovanni faction · keeps the Old Cemetery", clan: "hecata", generation: 10, hunger: 0, humanity: 6, bloodPotency: 3, lastVisionType: "Retrocognition", lastVisionWhen: "11 nights past", threadsCount: 0, draftsCount: 0 },
  { id: "100000000000000006", name: "Idris al-Najjar", epithet: "Judge of the Anarch Council", clan: "banuhaqim", generation: 8, hunger: 3, humanity: 7, bloodPotency: 3, lastVisionType: "The Witness", lastVisionWhen: "9 nights past", threadsCount: 1, draftsCount: 0 },
];

export function getKindred(id: string): KindredDetail | undefined {
  const base = ROSTER.find(k => k.id === id);
  if (!base) return undefined;

  if (id === "100000000000000001") {
    return {
      base,
      sire: "Vittoria della Rovere",
      embraced: "anno 1894",
      sect: "Camarilla",
      disciplineLabel: "Auspex · ●●●● · Scry the Soul unlocked",
      threads: [
        { title: "The Mirror's Reflection", whenOpened: "9 nights past", visionsCount: 4, isPrimary: true },
        { title: "Whispers in the Velvet", whenOpened: "3 nights past", visionsCount: 2 },
      ],
      symbols: [
        { name: "broken glass", count: 7 },
        { name: "red moths", count: 5 },
        { name: "the woman in white", count: 4 },
        { name: "a closed door", count: 3 },
        { name: "candlewax", count: 3 },
        { name: "violin string", count: 2 },
      ],
      recentVisions: [
        { type: "Resonance Bleed", when: "2 nights past", body: "Velvet curtains stir though no window is open. From beneath them seeps the scent of jasmine and copper, and a sound like a violin string drawn slowly across bone…" },
        { type: "Standard Vision", when: "5 nights past", body: "A hand you do not recognise sets a single red moth upon the rim of your glass. It does not burn though the candle is close. It watches." },
        { type: "The Warning", when: "8 nights past", body: "Do not return to the gallery on Calle Aviles. The painting you admire there has begun, lately, to admire you back." },
      ],
      drafts: [
        { id: "d1", type: "Resonance Bleed", body: "The mirror behind the bar has, all evening, refused your reflection. You thought yourself amused by it. Now, as the last mortal patron rises to leave, you catch what fills your absence there: a woman in white, seated where you sit, raising your glass to lips you cannot see. She drinks. The wine within your real glass lowers, exactly the measure she has taken.", when: "moments ago" },
        { id: "d2", type: "The Witness", body: "Someone has been counting your nights. You feel it in the way the doorman at the Pavilion no longer asks your name, and in how the new girl at the coat-check knows that you do not give up your coat.", when: "1 night past" },
        { id: "d3", type: "Echo Vision", body: "The violinist at the Belmont plays a melody you remember from a salon in Florence, the year before your Embrace. You have not heard the piece since.", when: "4 nights past" },
      ],
    };
  }
  return {
    base, sire: "unknown", embraced: "—", sect: "—",
    disciplineLabel: `Auspex · ${"●".repeat(Math.max(1, base.bloodPotency))}`,
    threads: [], symbols: [], recentVisions: [], drafts: [],
  };
}

export const SAMPLE_AI_DRAFTS = [
  "Tonight, every wineglass you pass holds a single red moth at its bottom, drowned and unmoving. The waiters notice nothing. When you lift one to your own table, the moth, very slowly, opens its wings.",
  "The woman in white is at your elbow before you hear her arrive. She does not speak. She places, on the marble in front of you, a small mirror. Your reflection in it is wearing a different coat than the one you have on tonight — the coat you wore the night you were Embraced.",
  "Somewhere beneath the city a violin is being tuned. You feel each adjustment as a small pull behind your sternum. When the player finally begins, you recognise the piece: it is the song you composed for Vittoria, the year she made you, and which you have told no one of since.",
];
