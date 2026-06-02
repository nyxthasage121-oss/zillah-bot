export function Pips({ filled, max = 5 }: { filled: number; max?: number }) {
  return (
    <div className="flex gap-1.5">
      {Array.from({ length: max }).map((_, i) => (
        <span key={i} className={"pip" + (i < filled ? " filled" : "")} />
      ))}
    </div>
  );
}

export function Dots({ filled, max = 10 }: { filled: number; max?: number }) {
  return (
    <div className="flex gap-1.5">
      {Array.from({ length: max }).map((_, i) => (
        <span key={i} className={"hdot" + (i < filled ? " filled" : "")} />
      ))}
    </div>
  );
}
