import { Clan } from "@/lib/mock-data";

const COLOR: Record<Clan, string> = {
  toreador: "#b08a3e",
  tremere: "#b03030",
  malkavian: "#8a4ab0",
  salubri: "#c9bfb0",
  hecata: "#6a8a4a",
  banuhaqim: "#4a8a8a",
};

export function ClanSigil({ clan, size = 32, opacity = 0.4 }: { clan: Clan; size?: number; opacity?: number }) {
  const c = COLOR[clan];
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" style={{ opacity }}>
      {clan === "tremere" && (
        <>
          <path d="M16 4 L26 22 L6 22 Z" stroke={c} strokeWidth="0.7" />
          <path d="M16 12 L20 19 L12 19 Z" stroke={c} strokeWidth="0.5" />
          <circle cx="16" cy="16" r="13" stroke={c} strokeWidth="0.3" />
        </>
      )}
      {clan === "malkavian" && (
        <>
          <circle cx="16" cy="16" r="13" stroke={c} strokeWidth="0.5" />
          <path d="M16 3 L16 29 M3 16 L29 16" stroke={c} strokeWidth="0.3" />
          <path d="M7 7 L25 25 M25 7 L7 25" stroke={c} strokeWidth="0.3" />
          <circle cx="16" cy="16" r="6" stroke={c} strokeWidth="0.5" strokeDasharray="2 2" />
        </>
      )}
      {clan === "hecata" && (
        <>
          <circle cx="16" cy="16" r="13" stroke={c} strokeWidth="0.5" />
          <path d="M16 6 L16 24 M10 16 L22 16" stroke={c} strokeWidth="0.7" />
          <circle cx="16" cy="16" r="3" stroke={c} strokeWidth="0.5" />
        </>
      )}
      {clan === "banuhaqim" && (
        <>
          <circle cx="16" cy="16" r="13" stroke={c} strokeWidth="0.5" />
          <path d="M16 5 L20 16 L16 27 L12 16 Z" stroke={c} strokeWidth="0.6" />
          <path d="M5 16 L27 16" stroke={c} strokeWidth="0.4" />
        </>
      )}
      {(clan === "toreador" || clan === "salubri") && (
        <>
          <circle cx="16" cy="16" r="14" stroke={c} strokeWidth="0.5" />
          <path
            d="M16 6 C 11 11, 11 16, 16 16 C 21 16, 21 11, 16 6 Z M6 16 C 11 11, 16 11, 16 16 C 16 21, 11 21, 6 16 Z M16 26 C 21 21, 21 16, 16 16 C 11 16, 11 21, 16 26 Z M26 16 C 21 21, 16 21, 16 16 C 16 11, 21 11, 26 16 Z"
            stroke={c}
            strokeWidth="0.5"
          />
        </>
      )}
    </svg>
  );
}
