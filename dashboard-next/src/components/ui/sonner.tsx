"use client";
import { Toaster as SonnerToaster, toast as sonnerToast } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-center"
      toastOptions={{
        unstyled: false,
        classNames: {
          toast:
            "bg-ink-850 border border-gold text-bone font-display tracking-[0.16em] uppercase text-[11px] !shadow-[0_12px_40px_-8px_rgba(0,0,0,0.8)]",
        },
      }}
    />
  );
}

export const toast = sonnerToast;
